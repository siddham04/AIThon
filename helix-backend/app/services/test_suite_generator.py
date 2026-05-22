"""Automated Test Generation — categorized.

Generates Functional / Negative / Boundary / Security / Regression
test cases for a requirement. Most tools stop after Functional —
this generator covers all five categories.
"""
from __future__ import annotations

import csv
import io
import logging
from typing import Any, Dict, List, Optional

from ..models import (
    GeneratedTest,
    GeneratedTestSuite,
    Severity,
    TestCategory,
    TestCategoryGroup,
)
from .ai_service import get_ai_service

logger = logging.getLogger("helix.test_suite_generator")


_CATEGORY_DESCRIPTIONS: Dict[TestCategory, str] = {
    TestCategory.FUNCTIONAL: "Happy-path and primary user flows.",
    TestCategory.NEGATIVE: "Wrong inputs, error states, conflicting data.",
    TestCategory.BOUNDARY: "Limits — empty, max length, off-by-one, edges.",
    TestCategory.SECURITY: "Authn/authz, injection, sensitive data exposure.",
    TestCategory.REGRESSION: "Adjacent flows that must keep working.",
}


# ---------- Heuristic ---------------------------------------------------- #


_FEATURE_KEYWORDS = [
    (("login", "auth", "sign-in"), "login"),
    (("otp", "2fa", "mfa"), "otp"),
    (("register", "sign-up"), "registration"),
    (("payment", "billing", "invoice"), "payment"),
    (("ticket", "support"), "ticketing"),
    (("notification", "email", "sms"), "notification"),
    (("upload", "attach"), "upload"),
    (("search", "find"), "search"),
]


def _detect_feature(text: str) -> str:
    low = text.lower()
    for needles, feature in _FEATURE_KEYWORDS:
        if any(n in low for n in needles):
            return feature
    return "feature"


# Static templates per category × feature
def _heuristic_tests(text: str) -> Dict[TestCategory, List[GeneratedTest]]:
    feature = _detect_feature(text)
    snippet = (text or "").strip().splitlines()[0][:80]

    out: Dict[TestCategory, List[GeneratedTest]] = {c: [] for c in TestCategory}

    # ---------- Functional ------------------------------------ #
    funcs = []
    if feature == "login":
        funcs.append(("Successful login with valid credentials",
                      "a registered user with valid email and password",
                      "they submit the login form",
                      "they are authenticated and a JWT session is issued"))
    if feature == "otp":
        funcs.append(("OTP delivery and verification",
                      "a user has triggered the OTP flow on a verified phone",
                      "they submit the 6-digit code within 5 minutes",
                      "they are authenticated and granted a session"))
    if feature == "registration":
        funcs.append(("Self-service account creation",
                      "an anonymous visitor on the sign-up page",
                      "they submit a unique email and a strong password",
                      "an account is created and a verification email is sent"))
    if feature == "ticketing":
        funcs.append(("Customer creates a support ticket",
                      "a logged-in customer on the support page",
                      "they submit subject + body + priority",
                      "a ticket is created with status=open and visible in their list"))
    if feature == "payment":
        funcs.append(("Successful card payment",
                      "a logged-in customer with a valid card",
                      "they submit a payment for a valid order",
                      "the payment status moves to captured and a receipt is issued"))
    if not funcs:
        funcs.append((f"Happy path for {snippet or feature}",
                      "the system is in its normal operating state",
                      f"the user performs {feature}",
                      "the system returns success and persists the change"))

    out[TestCategory.FUNCTIONAL] = [
        GeneratedTest(
            title=t, given=g, when=w, then=th,
            category=TestCategory.FUNCTIONAL, severity=Severity.HIGH,
            tags=["functional", feature],
            expected_result="200/201 OK with success payload",
        )
        for (t, g, w, th) in funcs
    ]

    # ---------- Negative ------------------------------------- #
    negs = []
    if feature in ("login", "otp"):
        negs.append(("Wrong credentials / OTP rejected",
                     "a registered user",
                     "they submit a wrong password or an incorrect OTP",
                     "the API returns 401 and the failure is rate-limit counted"))
    negs.append((f"{feature.title()} with malformed body",
                 "any caller",
                 f"they POST a malformed payload to the {feature} endpoint",
                 "the API returns 400 with a list of validation errors"))
    if feature == "registration":
        negs.append(("Reject duplicate email at sign-up",
                     "an email already belongs to an active account",
                     "a new visitor tries to register with that email",
                     "the API returns 409 conflict and no record is created"))
    if feature == "ticketing":
        negs.append(("Reject ticket update from a non-owner",
                     "ticket T owned by user A, currently logged in user B",
                     "B tries to modify ticket T",
                     "the API returns 403 forbidden"))

    out[TestCategory.NEGATIVE] = [
        GeneratedTest(
            title=t, given=g, when=w, then=th,
            category=TestCategory.NEGATIVE, severity=Severity.HIGH,
            tags=["negative", feature],
            expected_result="4xx with structured error",
        )
        for (t, g, w, th) in negs
    ]

    # ---------- Boundary ------------------------------------- #
    bnds = []
    if feature in ("login", "registration"):
        bnds.append(("Password at minimum length boundary",
                     "min length is 12 characters",
                     "the user submits a 12-character password",
                     "the request succeeds; an 11-char password is rejected"))
    if feature == "otp":
        bnds.append(("OTP at expiry boundary",
                     "an OTP that expires at T",
                     "the user submits the OTP at T-1s and at T+1s",
                     "T-1s succeeds, T+1s returns 410 expired"))
    if feature == "ticketing":
        bnds.append(("Subject at max length",
                     "subject column max length is 255",
                     "the user submits a 255-char subject and a 256-char one",
                     "255 is accepted, 256 is rejected with 400"))
    if feature == "payment":
        bnds.append(("Amount = 0 and amount = max int",
                     "the payment endpoint",
                     "the caller posts amount=0 and amount=2147483647",
                     "both are rejected with 400 invalid amount"))
    if not bnds:
        bnds.append(("Empty body",
                     "the endpoint expects a JSON body",
                     "the caller sends an empty {}",
                     "the API returns 400 with explicit missing-field errors"))

    out[TestCategory.BOUNDARY] = [
        GeneratedTest(
            title=t, given=g, when=w, then=th,
            category=TestCategory.BOUNDARY, severity=Severity.MEDIUM,
            tags=["boundary", feature],
            expected_result="Edge inputs handled deterministically",
        )
        for (t, g, w, th) in bnds
    ]

    # ---------- Security ------------------------------------- #
    secs = [
        (f"SQL injection in {feature} payload",
         "any string field on the endpoint",
         "the caller submits a SQLi payload (e.g. \"' OR 1=1 --\")",
         "the value is stored verbatim or rejected — never executed"),
        (f"Authentication required to call {feature}",
         "no Authorization header",
         f"the caller hits the {feature} endpoint",
         "the API returns 401 and does NOT leak data"),
        (f"Rate limiting on {feature}",
         "the same client",
         "issues 100 requests in 60 seconds",
         "the API returns 429 with a Retry-After header"),
    ]
    if feature in ("login", "otp"):
        secs.append(("Brute-force lockout",
                     "the same email",
                     "submits 5 wrong passwords or OTPs in a row",
                     "the account is locked for 15 minutes and a security event is logged"))
    if feature == "payment":
        secs.append(("PCI: no PAN in logs",
                     "a successful payment",
                     "logs are inspected for the request body",
                     "the full card number is masked or absent everywhere"))

    out[TestCategory.SECURITY] = [
        GeneratedTest(
            title=t, given=g, when=w, then=th,
            category=TestCategory.SECURITY, severity=Severity.CRITICAL,
            tags=["security", feature],
            expected_result="Attack is blocked or neutralized; no data leak",
        )
        for (t, g, w, th) in secs
    ]

    # ---------- Regression ----------------------------------- #
    regs = [
        (f"Pre-existing flows still work after {feature} change",
         f"the new {feature} feature has shipped",
         "the standard smoke suite is run",
         "all previously-green tests continue to pass"),
        ("API backwards-compat",
         f"the {feature} change touches a public endpoint",
         "an old client (v1 contract) calls it",
         "the request still succeeds; no breaking field changes"),
    ]
    if feature in ("login", "otp"):
        regs.append(("Existing sessions remain valid",
                     "users currently logged in",
                     f"the {feature} change is deployed mid-day",
                     "sessions stay valid and no forced logout occurs"))

    out[TestCategory.REGRESSION] = [
        GeneratedTest(
            title=t, given=g, when=w, then=th,
            category=TestCategory.REGRESSION, severity=Severity.MEDIUM,
            tags=["regression", feature],
            expected_result="Existing behavior unchanged",
        )
        for (t, g, w, th) in regs
    ]

    return out


def _to_groups(by_cat: Dict[TestCategory, List[GeneratedTest]]) -> List[TestCategoryGroup]:
    return [
        TestCategoryGroup(
            category=cat,
            description=_CATEGORY_DESCRIPTIONS[cat],
            tests=by_cat.get(cat, []),
        )
        for cat in TestCategory
    ]


# ---------- AI augmentation -------------------------------------------- #


_AI_SYSTEM = """You are a Senior Test Engineer. For each category
(Functional, Negative, Boundary, Security, Regression), produce 2-4
SPECIFIC, action-grounded tests. Use Given / When / Then. Avoid
generic platitudes. Every test must be plausibly executable.""".strip()


_AI_SCHEMA = """{
  "groups": [
    {
      "category": "functional|negative|boundary|security|regression",
      "tests": [
        {
          "title": "string — short, specific",
          "given": "string",
          "when": "string",
          "then": "string",
          "severity": "low|medium|high|critical",
          "tags": ["string"],
          "expected_result": "string"
        }
      ]
    }
  ]
}"""


_VALID_SEV = {s.value for s in Severity}
_VALID_CAT = {c.value for c in TestCategory}


def _coerce_test(raw: Any, cat: TestCategory) -> Optional[GeneratedTest]:
    if not isinstance(raw, dict):
        return None
    title = str(raw.get("title") or "").strip()
    if not title:
        return None
    sev_raw = str(raw.get("severity") or "medium").strip().lower()
    sev = Severity(sev_raw) if sev_raw in _VALID_SEV else Severity.MEDIUM
    return GeneratedTest(
        title=title[:160],
        category=cat,
        given=str(raw.get("given") or "").strip(),
        when=str(raw.get("when") or "").strip(),
        then=str(raw.get("then") or "").strip(),
        severity=sev,
        tags=[
            str(t).strip()
            for t in (raw.get("tags") or [])
            if str(t).strip()
        ][:6],
        expected_result=str(raw.get("expected_result") or "").strip(),
    )


async def _ai_groups(
    text: str,
    baseline: Dict[TestCategory, List[GeneratedTest]],
) -> Optional[Dict[TestCategory, List[GeneratedTest]]]:
    ai = get_ai_service()
    if not ai.enabled:
        return None
    base_blob = "\n".join(
        f"  {cat.value}: {len(tests)} tests"
        for cat, tests in baseline.items()
    )
    user = (
        f"Requirement:\n---\n{text[:4000]}\n---\n\n"
        f"Heuristic baseline counts:\n{base_blob}\n\n"
        f"Return ONLY JSON in this schema:\n{_AI_SCHEMA}"
    )
    try:
        data = await ai.complete_json(_AI_SYSTEM, user, max_tokens=5000)
    except Exception:  # pragma: no cover
        logger.exception("Test suite AI failed")
        return None

    out: Dict[TestCategory, List[GeneratedTest]] = {c: [] for c in TestCategory}
    for raw_group in data.get("groups") or []:
        try:
            cat_raw = str(raw_group.get("category") or "").strip().lower()
            if cat_raw not in _VALID_CAT:
                continue
            cat = TestCategory(cat_raw)
            for raw_t in raw_group.get("tests") or []:
                t = _coerce_test(raw_t, cat)
                if t is not None:
                    out[cat].append(t)
        except Exception:
            continue
    if not any(out.values()):
        return None
    return out


# ---------- Public API ------------------------------------------------- #


async def generate_test_suite(
    text: str,
    *,
    title: str = "",
    use_ai: bool = True,
) -> GeneratedTestSuite:
    baseline = _heuristic_tests(text)
    method = "heuristic"
    by_cat = baseline
    if use_ai:
        ai_out = await _ai_groups(text, baseline)
        if ai_out:
            # Merge: prefer AI tests; if AI missed a category entirely, fall back to heuristic.
            merged: Dict[TestCategory, List[GeneratedTest]] = {}
            for cat in TestCategory:
                merged[cat] = ai_out.get(cat) or baseline.get(cat, [])
            by_cat = merged
            method = "hybrid"

    groups = _to_groups(by_cat)
    total = sum(len(g.tests) for g in groups)
    summary = (
        f"{total} tests across "
        f"{sum(1 for g in groups if g.tests)} categories — "
        + ", ".join(
            f"{g.category.value}={len(g.tests)}"
            for g in groups
            if g.tests
        )
    )

    return GeneratedTestSuite(
        title=title or "Generated test suite",
        summary=summary,
        groups=groups,
        method=method,
    )


def to_simple_json(suite: GeneratedTestSuite) -> Dict[str, List[str]]:
    """Render the canonical shape:
    `{"Functional Tests": [...], "Negative Tests": [...], ...}`."""
    label_map = {
        TestCategory.FUNCTIONAL: "Functional Tests",
        TestCategory.NEGATIVE: "Negative Tests",
        TestCategory.BOUNDARY: "Boundary Tests",
        TestCategory.SECURITY: "Security Tests",
        TestCategory.REGRESSION: "Regression Tests",
    }
    out: Dict[str, List[str]] = {}
    for g in suite.groups:
        out[label_map[g.category]] = [t.title for t in g.tests]
    return out


def to_csv(suite: GeneratedTestSuite) -> str:
    buf = io.StringIO()
    w = csv.writer(buf, quoting=csv.QUOTE_ALL, lineterminator="\n")
    w.writerow([
        "Category", "Title", "Given", "When", "Then",
        "Severity", "Expected Result", "Tags",
    ])
    for g in suite.groups:
        for t in g.tests:
            w.writerow([
                g.category.value,
                t.title,
                t.given,
                t.when,
                t.then,
                t.severity.value,
                t.expected_result,
                ", ".join(t.tags),
            ])
    return buf.getvalue()
