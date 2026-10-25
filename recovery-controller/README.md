# Recovery Controller

The Recovery Controller is responsible for restoring failed microservices after the Monitoring Service records a failure event.

## Responsibilities

- Query PostgreSQL for unresolved failure events.
- Validate that the affected service is permitted for automatic recovery.
- Start stopped Docker containers using the local Docker CLI.
- Verify that recovered services respond to health checks.
- Record recovery duration, retry count and outcome.
- Apply cooldowns and retry limits to avoid continuous recovery attempts.

## Local execution

The controller runs as a Python process on the development computer.

```powershell
python recovery-controller/controller.py
```

## Security

Only explicitly allowlisted service containers can be started. The controller does not expose a public recovery API and does not execute arbitrary user-provided Docker commands.

## Limitations

This implementation supports one local controller process and recovery of existing stopped containers. It does not yet support distributed locking, replacement of deleted containers, or cloud orchestration.

In the AWS deployment, container replacement will be managed by Amazon ECS.