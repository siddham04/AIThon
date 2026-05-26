"""Regression tests for the demo-eve fixes:

* ``story_voice.normalize_*`` — turns LLM goal/benefit text into the
  shape the standard ``As a {persona}, I want {goal}, so that {benefit}.``
  template expects.

* ``quality_scorer._merge_missing`` veto — when the heuristic has strong
  keyword evidence for a dimension we must NOT let a hallucinated AI
  ``missing_information`` entry contradict it.

* ``quality_scorer._build_report`` blend — when the AI returns a score
  that is far harsher than the heuristic, the public score must NOT
  collapse to the AI value (the bug was 4 / F overriding 80 / B).

All tests run in mock mode and finish in well under a second.
"""
from __future__ import annotations

import asyncio
from typing import Any, Dict

import pytest

from app.services.story_voice import (
    normalize_benefit,
    normalize_goal,
    normalize_persona,
    normalize_voice,
)
from app.services.quality_scorer import (
    _build_report,
    _enterprise_dimensions,
    _heuristic_missing,
    _heuristic_score,
    _merge_missing,
    _well_covered_dimensions,
    score_requirement_text,
)


# --------------------------------------------------------------------- #
# story_voice                                                           #
# --------------------------------------------------------------------- #


class TestStoryVoice:
    def test_persona_strips_and_defaults(self) -> None:
        assert normalize_persona("Customer") == "Customer"
        assert normalize_persona("  Customer.  ") == "Customer"
        assert normalize_persona("") == "User"
        assert normalize_persona(None) == "User"

    def test_goal_lowercases_word_case_head(self) -> None:
        # Bug we shipped a fix for: AI returned "Place a service order"
        # and the template said "I want Place a service order".
        assert normalize_goal("Place a service order") == "place a service order"
        assert normalize_goal("Track my deliveries.") == "track my deliveries"

    def test_goal_preserves_acronyms(self) -> None:
        # "API" / "REST" / "OSS" must stay UPPERCASE.
        assert normalize_goal("API rate limiting works") == "API rate limiting works"
        assert normalize_goal("REST endpoints respond") == "REST endpoints respond"

    def test_goal_leaves_already_lowercase(self) -> None:
        assert normalize_goal("place a service order") == "place a service order"
        assert normalize_goal("to view my orders") == "to view my orders"

    def test_benefit_strips_to_prefix(self) -> None:
        # Bug we shipped a fix for: AI returned "to comply with X" and the
        # template said "so that to comply with X".
        assert (
            normalize_benefit("to comply with regulatory requirements")
            == "the team can comply with regulatory requirements"
        )

    def test_benefit_strips_in_order_to(self) -> None:
        # "in order to" is a verb-introducer → strip + rebuild clause.
        assert (
            normalize_benefit("in order to reduce risk")
            == "the team can reduce risk"
        )

    def test_benefit_dedupes_so_that_without_repairing_residue(self) -> None:
        # "so that" is the prefix the template itself emits — strip it
        # but DO NOT prepend a subject: the residue is already a clause.
        assert normalize_benefit("so that revenue grows") == "revenue grows"
        assert (
            normalize_benefit("so that customers receive timely notifications")
            == "customers receive timely notifications"
        )

    def test_benefit_leaves_clauses_with_subject(self) -> None:
        # Already grammatical — no surgery.
        assert (
            normalize_benefit("I can track delivery")
            == "I can track delivery"
        )
        assert (
            normalize_benefit("users can place orders without visiting a store")
            == "users can place orders without visiting a store"
        )
        assert (
            normalize_benefit("the team avoids manual re-keying")
            == "the team avoids manual re-keying"
        )

    def test_benefit_leaves_bare_verb_alone_when_no_prefix(self) -> None:
        # Deliberate non-decision: a leading uppercase word without a
        # verb-introducer prefix could be either a bare verb ("Comply
        # with X") or a noun ("Revenue grows"). We can't distinguish
        # without NLP, so the safer choice is to leave it alone. The
        # template will render "so that Comply with X" which is awkward
        # but still parseable — and crucially we don't break "Revenue
        # grows" into "the team can revenue grows".
        assert (
            normalize_benefit("Comply with regulatory requirements")
            == "Comply with regulatory requirements"
        )
        assert normalize_benefit("Revenue grows") == "Revenue grows"

    def test_normalize_voice_renders_clean_template(self) -> None:
        # End-to-end: feed the worst-case AI payload and reconstruct the
        # template — must not contain "I want Place" or "so that to".
        persona, goal, benefit = normalize_voice(
            "Retail Customer",
            "Place a service order for fiber broadband",
            "to quickly initiate service without visiting a store",
        )
        rendered = f"As a {persona}, I want {goal}, so that {benefit}."
        assert "I want Place" not in rendered
        assert "so that to " not in rendered
        assert rendered == (
            "As a Retail Customer, I want place a service order for fiber "
            "broadband, so that the team can quickly initiate service "
            "without visiting a store."
        )


# --------------------------------------------------------------------- #
# quality_scorer veto                                                   #
# --------------------------------------------------------------------- #


# A realistic PRD-sized snippet — short enough to keep tests fast but
# long enough (>= 200 words, multiple sections) that the heuristic
# scorer is in the band a real PRD lands in (60-90). A 56-word snippet
# would be auto-penalised by _heuristic_completeness's < 60 cutoff and
# would make the floor-protection test meaningless.
_TOMP_PRD_SNIPPET = """
Telecom Order Management Platform (TOMP) PRD v1.

User Roles. Customer can place service orders, track order status, upload
documents, and schedule installation. Sales Agent can create orders, modify
orders, and submit on behalf of customers. Provisioning Engineer can review
provisioning requests and resolve failures. Field Technician can receive
installation assignments and update status. Operations Administrator manages
products, workflows, and integrations. Each user role has explicit RBAC
permissions enforced by an audit-logged authorization layer.

Functional Requirements. FR-1: the system shall allow customers to create
service orders. FR-2: the system shall validate network availability,
coverage area, product eligibility, and service feasibility. FR-3: the
system shall integrate with external KYC services. FR-13: when processing
fails the system shall classify fallout, route to teams, track resolution.

Business Rules. BR-1: enterprise services above $50,000 require manager
approval. BR-2: fiber orders require network feasibility verification.
BR-3: failed KYC automatically cancels the order. BR-4: three provisioning
failures escalate to operations. BR-5: cancelled orders must release
reserved inventory. BR-6: installation appointments cannot overlap.

Non-Functional Requirements. Availability 99.99%. 95% of API responses
under 2 seconds. Support 10 million subscribers, 1 million monthly orders,
50,000 concurrent users. Security: MFA, RBAC, encryption at rest and in
transit, audit logging. Compliance: GDPR, ISO 27001, PCI-DSS.

Acceptance Criteria. Given coverage is available, When the customer submits
a valid order and completes KYC verification, Then the order shall be
accepted and an installation appointment shall be scheduled. Edge cases:
duplicate submissions must be rejected, concurrent modifications must be
serialised, expired KYC tokens must trigger re-verification.
""".strip()


class TestQualityScorerVeto:
    def test_heuristic_finds_well_covered_dimensions(self) -> None:
        # The snippet has roles + AC + business rules — none should be
        # flagged as missing by the heuristic.
        missing = _heuristic_missing(_TOMP_PRD_SNIPPET)
        dims_missing = {m.dimension.value for m in missing}
        assert "roles" not in dims_missing
        assert "success_criteria" not in dims_missing
        assert "business_rules" not in dims_missing

    def test_well_covered_dimensions_detects_strong_signals(self) -> None:
        covered = _well_covered_dimensions(_TOMP_PRD_SNIPPET, min_hits=3)
        covered_values = {d.value for d in covered}
        # roles: "customer", "user" (in "validate"? no), "role", "operator",
        # "stakeholder" — at least 3 hits in this snippet.
        assert "roles" in covered_values or "business_rules" in covered_values, (
            f"expected strong evidence for at least one major dimension, "
            f"got {covered_values}"
        )

    def test_ai_hallucination_cannot_invent_missing_actors(self) -> None:
        # Heuristic already saw "Customer", "user", "Sales Agent" — even if
        # the AI hallucinates "Missing actors" we must drop it.
        ai_missing = [
            {
                "dimension": "roles",
                "title": "Missing actors",
                "severity": "high",
                "explanation": "Hallucination — actors are present.",
                "suggested_question": "Who are the users?",
            }
        ]
        merged = _merge_missing(
            heuristic=[],
            ai_missing=ai_missing,
            text=_TOMP_PRD_SNIPPET,
        )
        assert all(m.dimension.value != "roles" for m in merged), (
            f"AI's 'Missing actors' was not vetoed: {[m.title for m in merged]}"
        )

    def test_ai_missing_still_kept_for_genuinely_absent_dimensions(self) -> None:
        # accessibility / scope have NO keyword hits in the snippet — AI
        # findings for those should be preserved.
        ai_missing = [
            {
                "dimension": "accessibility",
                "title": "Accessibility requirements not stated",
                "severity": "medium",
                "explanation": "No mention of WCAG.",
                "suggested_question": "What accessibility level is required?",
            }
        ]
        merged = _merge_missing(
            heuristic=[],
            ai_missing=ai_missing,
            text=_TOMP_PRD_SNIPPET,
        )
        titles = [m.title for m in merged]
        assert any("Accessibility" in t for t in titles), (
            f"genuine accessibility gap was vetoed by mistake: {titles}"
        )


# --------------------------------------------------------------------- #
# quality_scorer score blend                                            #
# --------------------------------------------------------------------- #


class TestQualityScorerBlend:
    def test_heuristic_alone_scores_tomp_above_b(self) -> None:
        # Sanity-floor: the comprehensive TOMP snippet should score
        # comfortably in the B band (>= 60) from the heuristic alone.
        report = asyncio.run(
            score_requirement_text(_TOMP_PRD_SNIPPET, use_ai=False)
        )
        assert report.overall_score >= 60, (
            f"heuristic score collapsed to {report.overall_score} — "
            f"check that completeness / specificity dimensions still "
            f"recognise this PRD's structure."
        )

    def test_runaway_ai_cannot_drag_score_to_F(self) -> None:
        # Simulate exactly the bug pattern: heuristic says ~80, AI says 4.
        # Expected: blended score stays well above the F threshold (55).
        h = _heuristic_score(_TOMP_PRD_SNIPPET)
        ai_dims: Dict[str, Any] = {
            "clarity": 5,
            "completeness": 4,
            "testability": 4,
            "ambiguity": 95,
            "overall_score": 4,
        }
        report = _build_report(
            h=h,
            quality=h["quality"],
            ambiguity=h["ambiguity"],
            merged_missing=[],
            merged_vague=[],
            clarifying=[],
            recommendations=[],
            method="hybrid",
            ai_dims=ai_dims,
        )
        # Blend formula: 0.7 * heuristic + 0.3 * AI when AI is much harsher.
        # Heuristic dims for this snippet land in the 60-90 band, so the
        # blended overall should be at least in the D band (>= 40) and
        # almost always in C (>= 55). Pinning >= 50 leaves a safety margin
        # for snippet-length differences without re-introducing the F bug.
        assert report.overall_score >= 50, (
            f"AI=4 dragged the blended score to {report.overall_score} — "
            f"the 0.7/0.3 floor protection in _build_report regressed."
        )
        assert report.grade in {"A", "B", "C", "D"}, report.grade
        # And the displayed score should never CRASH back to the raw AI 4.
        assert report.overall_score > 25


if __name__ == "__main__":  # pragma: no cover
    pytest.main([__file__, "-v"])
