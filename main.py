"""Local control-plane entrypoint; transports call ElianRuntime directly."""
from elian.planning import OpenAICompatiblePlanner
import os

from elian.permissions import PermissionPolicy
from elian.runtime import ElianRuntime

if __name__ == "__main__":
    runtime = ElianRuntime(planner=OpenAICompatiblePlanner.from_environment(), permission_policy=PermissionPolicy(os.getenv("ELIAN_PERMISSION_PROFILE", "standard")))
    print("Elian runtime is ready.")
    print("Planner configured:" if runtime.planner else "No planner configured; supply a validated plan or set ELIAN_MODEL_ENDPOINT, ELIAN_MODEL, and ELIAN_MODEL_API_KEY.", bool(runtime.planner))
    print(f"Recovered {len(runtime.recover())} interrupted task(s).")
