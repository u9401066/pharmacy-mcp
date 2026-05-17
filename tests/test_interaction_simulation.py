"""Tests for mechanism-aware interaction simulation."""

import pytest

from pharmacy_mcp.application.services.interaction import InteractionService


class TestInteractionSimulation:
    """Interaction service simulation tests."""

    @pytest.fixture
    def service(self) -> InteractionService:
        """Create interaction service."""
        return InteractionService()

    def test_explain_known_cyp_interaction_mechanism(self, service: InteractionService):
        """Known local DDI pairs expose mechanism and simulation readiness."""
        result = service.explain_interaction_mechanism("warfarin", "fluconazole")

        assert result["has_mechanism"] is True
        assert result["mechanism"]["pathway"] == "CYP2C9"
        assert result["mechanism"]["effect"] == "inhibition"
        assert result["simulation_ready"] is True
        assert "fm" in result["required_parameters"]
        assert result["not_for_direct_clinical_decision"] is True

    def test_unknown_pair_fails_open_for_lookup_but_closed_for_simulation(
        self,
        service: InteractionService,
    ):
        """Unknown pairs report no mechanism without guessing parameters."""
        result = service.explain_interaction_mechanism("unknown-a", "unknown-b")

        assert result["has_mechanism"] is False
        assert result["simulation_ready"] is False
        assert result["required_parameters"] == []

    def test_simulate_known_cyp_interaction_exposure(self, service: InteractionService):
        """Known CYP mechanism can be paired with explicit user-supplied parameters."""
        result = service.simulate_pk_interaction(
            drug1="simvastatin",
            drug2="clarithromycin",
            cl_total=10,
            fm=0.8,
            inhibitor_concentration=2,
            ki=1,
        )

        assert result["has_mechanism"] is True
        assert result["mechanism"]["pathway"] == "CYP3A4"
        assert result["simulation"]["outputs"]["auc_ratio"] == pytest.approx(
            2.14, abs=0.01
        )
        assert result["simulation"]["interaction_type"] == "cyp_reversible_inhibition"

    def test_simulate_unknown_pair_requires_known_mechanism(
        self, service: InteractionService
    ):
        """Simulation does not run when the interaction mechanism is unknown."""
        result = service.simulate_pk_interaction(
            drug1="unknown-a",
            drug2="unknown-b",
            cl_total=10,
            fm=0.8,
            inhibitor_concentration=2,
            ki=1,
        )

        assert (
            result["error"] == "No supported simulation mechanism found for this pair"
        )
        assert result["has_mechanism"] is False
