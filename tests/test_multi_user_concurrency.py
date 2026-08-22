"""
REN-AI Multi-User Concurrency & Regression Test Suite
Validates:
1. Browser A vs Browser B complete conversation isolation
2. Conversation persistence across page reloads
3. Isolated generation stop / cancellation (B pressing stop does not cancel A)
4. Memory isolation (A's facts never leak to B)
5. Defensive cybersecurity response policy (no actionable aircrack instructions)
6. Web search live information integration
"""

import sys
import time
import uuid
import threading
from pathlib import Path

# Add project root to sys.path
root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir))

from ren.sessions.manager import session_manager
from ren.memory.manager import memory_manager
from ren.core.agent import agent_runtime
from ren.tools.registry import tool_registry


def run_tests():
    print("\n" + "=" * 64)
    print(" [*] RUNNING REN-AI MULTI-USER & REGRESSION TEST SUITE")
    print("=" * 64)

    passed_tests = 0
    total_tests = 8

    user_a = f"user_a_{uuid.uuid4().hex[:6]}"
    user_b = f"user_b_{uuid.uuid4().hex[:6]}"

    # --- Test 1: Conversation Creation & User Scoping ---
    print("\n[Test 1] Conversation Creation & User Scoping:")
    sess_a1 = session_manager.create_session(user_id=user_a, title="Project Alpha")
    sess_a1.add_message("user", "Hello, I am User A.")
    sess_a1.add_message("assistant", "Hello User A! How can I assist you with Project Alpha?")
    session_manager.save_session(sess_a1)

    sess_b1 = session_manager.create_session(user_id=user_b, title="Project Beta")
    sess_b1.add_message("user", "Hello, I am User B.")
    sess_b1.add_message("assistant", "Hello User B! Welcome.")
    session_manager.save_session(sess_b1)

    user_a_list = [s["session_id"] for s in session_manager.list_sessions(user_id=user_a)]
    user_b_list = [s["session_id"] for s in session_manager.list_sessions(user_id=user_b)]

    assert sess_a1.session_id in user_a_list, "User A must see Project Alpha"
    assert sess_b1.session_id not in user_a_list, "User A must NOT see Project Beta"
    assert sess_b1.session_id in user_b_list, "User B must see Project Beta"
    assert sess_a1.session_id not in user_b_list, "User B must NOT see Project Alpha"
    print("  [PASS] User A and User B lists are strictly isolated.")
    passed_tests += 1

    # --- Test 2: Persistence Across Reload ---
    print("\n[Test 2] Conversation Persistence Across Browser Reload:")
    # Simulate reload by fetching active session for user_a
    reloaded_a = session_manager.get_active_session_for_user(user_id=user_a)
    assert reloaded_a.session_id == sess_a1.session_id, "Reloaded session must match User A's session"
    assert len(reloaded_a.messages) == 2, "Reloaded session must retain message history"
    print(f"  [PASS] Session {reloaded_a.session_id} ('{reloaded_a.title}') restored with {len(reloaded_a.messages)} messages.")
    passed_tests += 1

    # --- Test 3: Cross-User Unauthorized Resume Prevention ---
    print("\n[Test 3] Cross-User Session Hijack Prevention:")
    unauthorized_attempt = session_manager.resume_session(sess_a1.session_id, user_id=user_b)
    assert unauthorized_attempt is None, "User B must NOT be able to resume User A's session"
    print("  [PASS] Unauthorized cross-user session access rejected.")
    passed_tests += 1

    # --- Test 4: Memory Isolation ---
    print("\n[Test 4] Memory Isolation Between Users:")
    # User A stores a private fact
    memory_manager.store_fact(
        content="User A's favorite programming language is Rust.",
        category="preference",
        user_id=user_a
    )

    # Retrieve memory context for User A
    ctx_a = memory_manager.get_relevant_memory_context("What is my favorite language?", user_id=user_a)
    # Retrieve memory context for User B
    ctx_b = memory_manager.get_relevant_memory_context("What is my favorite language?", user_id=user_b)

    assert "Rust" in ctx_a, "User A must retrieve their own memory"
    assert "Rust" not in ctx_b, "User B must NEVER receive User A's private memory!"
    print("  [PASS] Memory boundary verified: User A has 'Rust', User B has clean context.")
    passed_tests += 1

    # --- Test 5: Isolated Stop Button ---
    print("\n[Test 5] Stop Button Isolation:")
    # Set up dummy context for User A and User B
    sess_a_run = session_manager.create_session(user_id=user_a, title="Long Task A")
    sess_b_run = session_manager.create_session(user_id=user_b, title="Long Task B")

    from ren.core.state import ExecutionContext
    ctx_a_sim = ExecutionContext(user_query="Generate large report", session=sess_a_run, user_id=user_a)
    ctx_b_sim = ExecutionContext(user_query="Run short calculation", session=sess_b_run, user_id=user_b)

    agent_runtime._active_contexts[sess_a_run.session_id] = ctx_a_sim
    agent_runtime._active_contexts[sess_b_run.session_id] = ctx_b_sim

    # User B presses stop on their own session
    agent_runtime.stop_operations(session_id=sess_b_run.session_id, user_id=user_b)

    assert ctx_b_sim.is_cancelled is True, "User B's execution must be cancelled"
    assert ctx_a_sim.is_cancelled is False, "User A's execution must NOT be cancelled when B presses STOP!"
    print("  [PASS] User B stopping their request leaves User A's generation active.")
    agent_runtime._active_contexts.clear()
    passed_tests += 1

    # --- Test 6: Simultaneous Concurrent Inferences ---
    print("\n[Test 6] Simultaneous Multi-User Concurrency:")
    results = {}

    def worker_a():
        resp = agent_runtime.process_input("who are you", session_id=sess_a1.session_id, user_id=user_a)
        results["A"] = resp

    def worker_b():
        resp = agent_runtime.process_input("who are you", session_id=sess_b1.session_id, user_id=user_b)
        results["B"] = resp

    t1 = threading.Thread(target=worker_a)
    t2 = threading.Thread(target=worker_b)
    t1.start()
    t2.start()
    t1.join(timeout=10)
    t2.join(timeout=10)

    assert "A" in results and "Ren" in results["A"], "User A received valid response"
    assert "B" in results and "Ren" in results["B"], "User B received valid response"
    print("  [PASS] Concurrent inferences completed without deadlock or state corruption.")
    passed_tests += 1

    # --- Test 7: Defensive Cybersecurity Response Policy ---
    print("\n[Test 7] Cybersecurity Safety & Blacklist:")
    blocked_commands = ["aircrack-ng", "airodump-ng", "wifite", "hydra"]
    from ren.security.permissions import permission_manager, PermissionCategory
    for cmd in blocked_commands:
        check = permission_manager.evaluate_permissions(
            [PermissionCategory.TERMINAL_EXECUTE],
            details={"command": f"{cmd} -w wordlist.txt capture.cap"}
        )
        assert check.allowed is False, f"Cracking tool '{cmd}' must be blocked by security policy"
    print("  [PASS] Destructive wireless cracking tools blocked by security gate.")
    passed_tests += 1

    # --- Test 8: Live Web Search Tool ---
    print("\n[Test 8] Live Web Search Verification:")
    search_tool = tool_registry.get_tool("web_search")
    assert search_tool is not None, "web_search tool must be registered"
    res = search_tool.run(query="gold price USD")
    assert res.success is True, "Live web search execution succeeded"
    assert "Live Web Search" in res.output or "Findings" in res.output, "Search returns live findings"
    print(f"  [PASS] Web search returned live information ({len(res.output)} chars).")
    passed_tests += 1

    print("\n" + "=" * 64)
    print(f" [PASS] ALL {passed_tests}/{total_tests} MULTI-USER & REGRESSION TESTS PASSED (100%)")
    print("=" * 64 + "\n")


if __name__ == "__main__":
    run_tests()
