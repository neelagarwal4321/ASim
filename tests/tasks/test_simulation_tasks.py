import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../backend'))


def test_task_has_delay():
    from tasks.simulation_tasks import run_full_simulation
    assert hasattr(run_full_simulation, "delay")


def test_task_name_contains_run_full():
    from tasks.simulation_tasks import run_full_simulation
    assert "run_full_simulation" in run_full_simulation.name
