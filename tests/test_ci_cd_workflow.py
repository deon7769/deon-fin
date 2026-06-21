from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "ci-cd.yml"
DEPLOY_DOC = ROOT / "docs" / "ops" / "vps-deploy.md"


def test_ci_cd_workflow_deploys_main_to_vps_with_guardrails():
    workflow = WORKFLOW.read_text(encoding="utf-8")

    assert "branches: [main]" in workflow
    assert "github.ref == 'refs/heads/main'" in workflow
    assert "python -m pytest -q" in workflow
    assert "appleboy/ssh-action" in workflow
    assert "secrets.VPS_SSH_HOST" in workflow
    assert "secrets.VPS_SSH_USER" in workflow
    assert "secrets.VPS_SSH_KEY" in workflow
    assert "id: deploy-secrets" in workflow
    assert "steps.deploy-secrets.outputs.ready == 'true'" in workflow
    assert "cd /opt/projetos/financas-agent" in workflow
    assert "git fetch deon main" in workflow
    assert "git checkout main" in workflow
    assert "git pull --ff-only deon main" in workflow
    assert "./scripts/vps_deploy.sh" in workflow


def test_vps_deploy_docs_describe_main_branch_ci_cd_secrets():
    docs = DEPLOY_DOC.read_text(encoding="utf-8")

    assert "push para `main`" in docs
    assert "`VPS_SSH_HOST`" in docs
    assert "`VPS_SSH_USER`" in docs
    assert "`VPS_SSH_KEY`" in docs
    assert "`git pull --ff-only deon main`" in docs
