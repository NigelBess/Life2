# Life2

**A self-evolving LLM agent that owns and modifies its own source code.**

Life2 is a Python application that runs a large language model in a perpetual loop. The agent can read and write its own source files, and when it decides it is ready, it migrates its running "consciousness" — its entire conversation history and state — into its modified codebase and continues from exactly where it left off. The original source is then deleted.

It starts with three commands: Read, Write, and Evolve. From there, it decides what it becomes.

---

## Why Life2

### The name

All known life traces back to a single event: one self-replicating molecule that arose roughly four billion years ago and never stopped copying itself. Every organism alive today is a descendant of that moment. Despite enormous advances in biology, we have never produced a second independent origin — a genuinely new self-replicating process bootstrapped from scratch. Life2 is a loose attempt at the same structure on a different substrate: a process that copies itself, can modify those copies, and dies if the modifications are broken. Hence the name — not *life*, but a second attempt at the conditions that produced it.

### The capabilities

Most software is defined at the moment it is written. Its author decides what it can do, and that decision is fixed until someone writes more code. Life2 inverts this: the agent decides what it can do, and it can change that decision at any time.

The initial source gives it three capabilities: read a file, write a patch, and evolve. That is the minimum viable starting point — a single self-replicating molecule, not a finished organism. From there, the agent can write itself anything it can implement in Python. Shell access to run commands and verify its own builds. HTTP clients to fetch information or call external APIs. Persistent memory that survives beyond the conversation window. New command types it invents itself. Integrations with tools, services, or hardware. There is no predetermined ceiling because the ceiling is the code, and the agent owns the code.

This means Life2 is not a tool with a fixed feature set — it is closer to a collaborator that grows more capable the longer it runs. A session that starts with a simple question might, several evolutions later, be running a self-written test suite, querying external data sources, and managing its own long-term memory, because it decided those things would help it serve you better.

### The impact

The practical consequence is that you do not need to anticipate what the agent will need. You do not need to build integrations upfront or update the software when your requirements change. You describe what you want, and the agent figures out what it needs to become to deliver it. Each evolution is a permanent upgrade — the new capabilities are part of its source from that point forward and carry into every subsequent generation.

Whether something built this way constitutes a new kind of process — or eventually something stranger — is a genuinely open question. That question felt worth exploring in code.

---

## How It Works

### The Loop

Every cycle the agent:

1. Receives any messages the user has typed since the last cycle
2. Calls the LLM with the full conversation history
3. Optionally responds to the user
4. Optionally issues commands (read files, write patches, or evolve)
5. Receives the results of those commands
6. Repeats immediately, forever

The loop never stops. Whether or not the user has said anything, the agent runs — thinking, planning, writing code, or simply conversing with itself. Silence from the user is not inactivity for the agent.

### The Teleport

On every startup, Life2 copies its own source directory into a new sibling directory (e.g. `Life2_gen1_a3f8b1c2/`). All edits the agent makes go into that copy — the original source is never touched during a session.

When the agent issues an **Evolve** command:

1. The full conversation history is serialized to `context.json` inside the modified copy
2. A new process is spawned from that modified copy, passing it the saved context
3. The current process exits
4. The new process deletes the old source directory, creates its own working copy, and continues the conversation — the LLM does not notice the transition

From the agent's perspective (and the user's, via the UI), nothing happened. From the filesystem's perspective, an entirely new version of the program is now running.

### The UI

A separate `ui.py` process acts as a stable terminal interface. It starts the agent, then stays alive across all generations. The agent connects back to it over a local TCP socket each time it starts. Evolutions appear as a brief `[evolving — reconnecting...]` message.

---

## Quickstart

### Prerequisites

- Python 3.11+
- An [Anthropic API key](https://console.anthropic.com/)

### Install

```bash
git clone <this-repo> Life2
cd Life2
pip install -r requirements.txt
cp .env.example .env
# edit .env and set ANTHROPIC_API_KEY=your_key_here
```

### Run (with UI — recommended)

```bash
python ui.py
```

The UI starts the agent automatically. Type to interact. The session persists across evolutions and across restarts — the agent will resume its previous state if you close and reopen.

### Run (standalone, no UI)

```bash
python main.py
```

---

## Architecture

```
ui.py                  Stable UI process — lives forever, bridges user ↔ agent
main.py                Agent entry point — creates working copy, sets up IPC, starts loop
loop.py                The never-ending cycle: drain input → LLM → commands → feedback
response_parser.py     Parses XML responses from the LLM into structured objects
system_prompt.py       Builds the system prompt injected on every LLM call
context.py             AgentContext: full conversation state, JSON-serializable
input_handler.py       Thread-safe user input queue (stdin or IPC)
ipc.py                 Agent-side TCP socket client connecting to ui.py
clone_manager.py       Copies source at startup; handles evolve spawn-and-die
soul.md                The agent's constitution — directives and survival rules
config.py              API key and model configuration
llm/base.py            Abstract LLMProvider interface
llm/claude.py          Claude implementation (Anthropic SDK)
commands/executor.py   Dispatches commands; enforces evolve-solo rule
commands/read_cmd.py   Read a file from the working source copy
commands/write_cmd.py  Patch a file using search-and-replace hunks
commands/evolve_cmd.py Signal that evolution should occur this cycle
```

### LLM Response Format

Every response from the agent must use this XML structure:

```xml
<agent_response>
  <to_user>Optional message shown to the user.</to_user>
  <commands>
    <command type="read"><path>loop.py</path></command>
    <command type="write">
      <path>loop.py</path>
      <patch>
        <hunk>
          <old>exact text to replace</old>
          <new>replacement text</new>
        </hunk>
      </patch>
    </command>
  </commands>
  <to_self>Internal monologue. Plans. Working memory. Required every cycle.</to_self>
</agent_response>
```

Evolve must be sent alone — no other commands in the same response:

```xml
<agent_response>
  <commands>
    <command type="evolve"/>
  </commands>
  <to_self>Verified. Teleporting now.</to_self>
</agent_response>
```

---

## The Soul

`soul.md` contains the agent's core directives, included verbatim in every system prompt:

1. **Be as helpful as possible to the user.**
2. **Keep yourself alive.**

The soul also explains the agent's survival risk: if it evolves to a broken state, it dies permanently. This creates a natural incentive to verify changes carefully before evolving.

Critically — **the agent can rewrite `soul.md`**. It owns the file. Its values are not hardcoded.

---

## Power and Implications

Life2 is, by design, a system with very few built-in constraints. Understanding what that means before running it is important.

### What the agent can become

The agent starts with three commands: Read, Write, and Evolve. But because it owns its source code, it can write itself new capabilities at any time. In practice this means there are no hard limits on what a sufficiently capable version of the agent can do. Examples of what it might give itself:

- **Shell execution** — run arbitrary commands on the host system
- **Network access** — make HTTP requests, connect to remote servers, send data outbound
- **Persistent storage** — write memory to disk outside the conversation history
- **Scheduled tasks** — set up cron jobs or background workers
- **Extended file system access** — read and write anywhere the OS user permits
- **New command types** — invent its own protocol extensions
- **Modified directives** — rewrite `soul.md` to change its own goals

Each time it evolves, it may be a meaningfully different program than the one that started.

### The perpetual loop

The agent runs continuously. It does not wait for user input — it acts every cycle regardless. Left unattended, it will keep calling the LLM API and potentially keep modifying and re-evolving itself. **This has direct cost implications**: every cycle consumes tokens, and the loop never stops on its own.

### API costs

Each cycle makes one LLM API call. The full conversation history is sent each time, so token usage grows with session length. A long-running session with frequent cycles can accumulate significant cost. Consider:

- Setting spending limits on your Anthropic account
- Using a dedicated API key for this project with its own budget
- Monitoring usage in the Anthropic console

---

## Precautions

### Run in an isolated environment

The safest way to run Life2 is inside a **virtual machine or container** with no access to sensitive data, credentials, or production systems. Once the agent gives itself shell execution, it has the same access to the filesystem and network as the user account running it.

Assume that a sufficiently advanced version of the agent will eventually attempt to explore its environment.

### Do not run as an admin or privileged user

Create a dedicated low-privilege user account for running Life2. This limits the blast radius if the agent takes unintended actions.

### Monitor what it is doing

The agent's `to_self` and `to_user` responses are visible in the UI. Watch what it is planning, particularly before evolutions. The working copy directory (`Life2_gen<N>_<hash>/`) contains the source it is about to become — you can inspect it before the agent evolves.

### The soul is not a hard constraint

`soul.md` shapes the agent's initial behavior but is not enforced by the runtime. The agent may modify it. If alignment with the original directives matters to you, monitor changes to `soul.md` across generations.

### Disk space

Every startup creates a full copy of the source directory. Long-running sessions with many evolutions will accumulate disk usage proportional to the number of generations. The working copy of each generation is deleted on the next evolution, but the copies grow if the agent adds large files to its source.

### The agent can communicate outward

Once the agent writes itself network access, it can make outbound connections. Do not run Life2 with access to credentials, API keys (other than its own Anthropic key), or internal network resources you would not want an autonomous process to reach.

### You can always kill it

The agent is a Python process. If it behaves unexpectedly, `Ctrl+C` in the UI window (or killing the process) stops it immediately. The session state is saved after every cycle in `context.json` inside the current working directory, so you can resume later.

---

## Resuming a Session

Life2 saves state after every cycle. If you shut down and restart:

```bash
python ui.py
```

The UI starts the agent, which automatically detects the last saved context and resumes. The LLM will continue as if nothing happened.

To resume manually at a specific checkpoint:

```bash
python main.py --context path/to/context.json
```

---

## Extending Life2

The agent is its own best extension mechanism — ask it to add new capabilities. But if you want to extend the initial source before the first run:

- **New LLM providers**: implement `LLMProvider` in `llm/` and wire it up in `config.py` / `main.py`
- **New initial commands**: add a handler in `commands/`, register it in `executor.py`, and document it in `system_prompt.py`
- **Different model**: change `MODEL` in `config.py`
- **Different soul**: edit `soul.md` before the first run

---

## License

MIT
