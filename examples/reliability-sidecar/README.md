# General agent plus reliability sidecar

This example composes the live, free Workflow Guard Planner with a deliberately
small mock domain agent. The sidecar selects an honest guard profile; the
domain agent still owns search, creation, and read-back.

Run it from the repository root with Python 3.10 or later:

```sh
python -B examples/reliability-sidecar/run.py
```

The script uses only Python's standard library. It:

1. initializes the progressive MCP endpoint;
2. searches for and describes the planner before invocation;
3. asks the planner about a retryable duplicate-sensitive create;
4. runs the mock domain operation twice with one stable marker; and
5. proves the mock destination contains one record while preserving the
   planner's residual-risk warnings.

Set `AGENT_ENHANCER_MCP_URL` to exercise another compatible deployment. Never
put credentials, private records, or personal data in the planner contract.
The example does not claim exactly-once execution across two independent
services. Its default URL adds the aggregate source tag
`github-example-sidecar`; the untagged endpoint behaves the same way.
