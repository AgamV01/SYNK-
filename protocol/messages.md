# protocol/messages.md

Authoritative WebSocket message contract for SYNK. The Python server and the TypeScript SDK implement exactly what is written here.

Authored in full during fix_plan tasks in the Protocol phase, derived from spec section 6. It must define, for every message, the `type` string, the `v` version, and the exact field shapes, plus: the `world_state` throttle rate, the "nearby" radius for overhearing, the facing representation, and the `agent_event` kinds that structured LLM actions surface as. Include a small JSON example for each message.

Until the Protocol phase tasks are done, treat spec section 6 as the contract.
