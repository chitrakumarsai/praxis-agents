"""Content checks for the packs bundled in ``praxis/packs``."""

import re
from pathlib import Path

import pytest

from praxis_agents.adapters import agents_md
from praxis_agents.bundled import available_packs, pack_source
from praxis_agents.loader import load_pack
from praxis_agents.model import ForbidCheck, Pack
from praxis_agents.sync import managed_block
from praxis_agents.verify import verify

PACK_NAMES = available_packs()

# Always-on rules are loaded on every request; keep them short enough to be followed.
MAX_RULE_LINES = 160
REFERENCE_LINK = re.compile(r"`((?:references|scripts|assets)/[^`]+)`")


def test_agent_engineering_pack_is_bundled():
    assert "agent-engineering" in PACK_NAMES


@pytest.mark.parametrize("name", PACK_NAMES)
def test_pack_rules_fit_budget(name):
    with pack_source(name) as source:
        rendered = agents_md.render(load_pack(source))

    (agents,) = [output for output in rendered if output.path == agents_md.PATH]
    assert len(managed_block(agents.content).splitlines()) <= MAX_RULE_LINES


@pytest.mark.parametrize("name", PACK_NAMES)
def test_skill_reference_links_resolve(name):
    with pack_source(name) as source:
        pack = load_pack(source)

    for skill in pack.skills:
        shipped = {ref.path for ref in skill.references} | {res.path for res in skill.resources}
        assert set(REFERENCE_LINK.findall(skill.body)) <= shipped, skill.name


# Every bundled check is a grader: prove it flags known-bad lines and passes known-good ones.
# Keys are rule ids; a check without examples here fails test_every_bundled_check_has_examples.
# Fake credentials are assembled at runtime so this file never contains a literal one.
FAKE = "x" * 40
CHECK_EXAMPLES = {
    "classify-before-retry": (
        ["@retry", "    @retry()", "@tenacity.retry", "  @tenacity.retry( )"],
        [
            "@retry(stop=stop_after_attempt(3), wait=wait_exponential())",
            "@tenacity.retry(stop=stop_after_delay(30))",
            "# never use a bare retry decorator",
            "def retry():",
        ],
    ),
    "tool-contracts": (
        ["except:", "    except :", "except Exception: pass", "except Exception as exc: ...",
         "    except BaseException:  pass"],
        [
            "except ValueError:",
            "except Exception as exc:",
            "except (OSError, TimeoutError) as exc:",
            "    raise ToolError('timeout') from exc",
            "# an except: clause hides failures",
        ],
    ),
    "untrusted-content": (
        [
            "-----BEGIN RSA " + "PRIVATE KEY-----",
            "-----BEGIN " + "PRIVATE KEY-----",
            "key = 'AKIA" + "ABCDEFGHIJKLMNOP'",
            "ANTHROPIC_API_KEY=sk-" + "ant-api03-" + FAKE,
            "OPENAI_API_KEY=sk-" + "proj-" + FAKE,
            "token: ghp_" + "A" * 36,
            "SLACK=xoxb-" + "1234567890-abcdef",
            "subprocess.run(cmd, shell" + "=True)",
            # Connection URLs with a literal password (assembled so this file holds none).
            "DATABASE_URL=postgresql+psycopg://admin:" + "s3cret-pass@db:5432/app",
            "REDIS_URL=redis://default:" + "hunter2@cache:6379/0",
            'client = MongoClient("mongodb+srv://app:' + 'Xy9pass@cluster0.example.net/db")',
            "BROKER=amqp://guest:" + "guest@localhost:5672/",
            "git clone https://bot:" + "abc123token@github.com/org/repo.git",
        ],
        [
            "api_key = os.environ['ANTHROPIC_API_KEY']",
            "-----BEGIN PUBLIC KEY-----",
            "subprocess.run(['git', 'status'], shell=False)",
            "sk-ant-... (placeholder in docs)",
            "AKIA is the prefix of AWS access key ids",
            "the shell is untrusted",
            # Near misses: no literal password in the URL.
            "DATABASE_URL=postgresql://${DB_USER}:${DB_PASSWORD}@db:5432/app",
            'url = f"postgresql://{user}:{password}@{host}/app"',
            "postgresql://<user>:<password>@<host>/<db>",
            "postgresql://app:***@db/app",
            "postgresql://app@localhost/app",
            "API=http://localhost:8000/api/chats/",
            "git@github.com:org/repo.git",
            "see https://example.com/docs?user=me&page=2",
        ],
    ),
}


def _bundled_rules_with_checks():
    for name in PACK_NAMES:
        with pack_source(name) as source:
            yield from (rule for rule in load_pack(source).rules if rule.checks)


def _flagged(rule, line):
    (result,) = verify(Pack(rules=(rule,)), {"src/example.py": ((1, line),)}, Path("."))
    return result.status == "fail"


def test_every_bundled_check_has_examples():
    assert {rule.id for rule in _bundled_rules_with_checks()} == set(CHECK_EXAMPLES)


def test_bundled_checks_are_forbid_only():
    # `run` commands are project-specific; a bundled pack must not execute anything.
    for rule in _bundled_rules_with_checks():
        assert all(isinstance(check, ForbidCheck) for check in rule.checks), rule.id


@pytest.mark.parametrize("rule_id", sorted(CHECK_EXAMPLES))
def test_bundled_checks_flag_bad_and_pass_good_lines(rule_id):
    (rule,) = [rule for rule in _bundled_rules_with_checks() if rule.id == rule_id]
    bad, good = CHECK_EXAMPLES[rule_id]

    assert [line for line in bad if not _flagged(rule, line)] == []
    assert [line for line in good if _flagged(rule, line)] == []


def test_process_rules_are_not_sent_to_the_judge():
    # A diff can't show whether success was defined first or cost is measured; grading these
    # wastes requests and produced false failures in the live smoke test.
    with pack_source("agent-engineering") as source:
        skipped = {rule.id for rule in load_pack(source).rules if not rule.judge}

    assert skipped == {
        "define-success-first",
        "evaluate-continuously",
        "cost-per-verified-success",
        "fix-the-right-layer",
    }
