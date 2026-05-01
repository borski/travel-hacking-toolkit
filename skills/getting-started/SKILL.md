---
name: getting-started
description: User-invoked first-run setup. Detects which API keys are configured, points the user at the local setup-keys script (so secrets never go through chat), and shows sample prompts scaled to what they have. Use when the user types /travel-hacker:getting-started, asks "how do I use this", or runs the toolkit for the first time.
disable-model-invocation: true
category: orchestration
summary: First-run onboarding. Detects setup, points to setup-keys script, shows sample prompts.
license: MIT
---

# Getting Started Skill

The user invoked this skill explicitly. Help them figure out what's already working, what they're missing, and what to actually try. Critically: **do NOT prompt for API keys in chat.** Pasting a key into a chat input puts it in terminal scrollback, the local Claude Code session log, and the Anthropic API logs. The toolkit ships a local script that prompts for keys with masked input and writes them straight to the user's shell rc, never going through chat.

## Step 1: Detect what's already configured

First detect the user's platform via the Bash tool's environment. If `bash` is available (macOS, Linux, WSL, Git Bash on Windows), use the bash detection. If you're on native Windows PowerShell with no bash, use the PowerShell detection instead.

Don't print the values; only report SET vs MISSING.

### Bash (macOS / Linux / WSL / Git Bash)

```bash
for var in SEATS_AERO_API_KEY DUFFEL_API_KEY_LIVE IGNAV_API_KEY AWARDWALLET_API_KEY AWARDWALLET_USER_ID SERPAPI_API_KEY RAPIDAPI_KEY LITEAPI_API_KEY TRIPADVISOR_API_KEY ENTUR_CLIENT_NAME RESROBOT_API_KEY REJSEPLANEN_API_KEY; do
  if [ -n "${!var:-}" ]; then echo "SET: $var"; else echo "MISSING: $var"; fi
done
```

### PowerShell (native Windows)

```powershell
$keys = @('SEATS_AERO_API_KEY','DUFFEL_API_KEY_LIVE','IGNAV_API_KEY','AWARDWALLET_API_KEY','AWARDWALLET_USER_ID','SERPAPI_API_KEY','RAPIDAPI_KEY','LITEAPI_API_KEY','TRIPADVISOR_API_KEY','ENTUR_CLIENT_NAME','RESROBOT_API_KEY','REJSEPLANEN_API_KEY')
foreach ($k in $keys) {
    $v = [Environment]::GetEnvironmentVariable($k)
    if ([string]::IsNullOrEmpty($v)) { Write-Host "MISSING: $k" } else { Write-Host "SET: $k" }
}
```

Group the results:

**Tier 1 (high-value, missing matters most):** SEATS_AERO_API_KEY, DUFFEL_API_KEY_LIVE, IGNAV_API_KEY, AWARDWALLET_API_KEY + AWARDWALLET_USER_ID

**Tier 2 (extra sources):** SERPAPI_API_KEY, RAPIDAPI_KEY, LITEAPI_API_KEY, TRIPADVISOR_API_KEY

**Tier 3 (specific use cases):** ENTUR_CLIENT_NAME, RESROBOT_API_KEY, REJSEPLANEN_API_KEY (Scandinavia transit only)

## Step 2: Tell the user where they stand

Be concrete. Examples:

- All Tier 1 set: "You're fully configured. Skip to step 4 (sample prompts)."
- All missing: "You haven't set any API keys yet. The 5 free MCP servers (Skiplagged, Kiwi, Trivago, Ferryhopper, Airbnb) work without keys, so you can already search cash flights and hotels. Add keys to unlock award search and balance auto-pull."
- Some Tier 1 set: "You have X of 4 high-value keys. The setup script can add the missing ones."

## Step 3: Point the user at the local setup script

If keys are missing and the user wants to add them, give them the right command for their platform. Detect their shell with `echo $SHELL` and OS with `uname`.

### macOS / Linux / WSL / Git Bash

> "Run this in your terminal (NOT in this chat). The script asks for each key with masked input, validates them, and writes the exports to your shell rc with a backup. Your keys never go through this chat session.
>
> ```bash
> bash <(curl -fsSL https://raw.githubusercontent.com/borski/travel-hacking-toolkit/main/scripts/setup-keys.sh)
> ```
>
> Or if you have the repo cloned: `bash scripts/setup-keys.sh`
>
> When it's done, run `source ~/.zshrc` (or `~/.bashrc`, or your fish config) and ask me to plan a trip."

### Windows (PowerShell)

> "Run this in PowerShell (NOT in this chat). The script asks for each key with masked input and writes them to your PowerShell profile.
>
> ```powershell
> iwr https://raw.githubusercontent.com/borski/travel-hacking-toolkit/main/scripts/setup-keys.ps1 -OutFile $env:TEMP\setup-keys.ps1
> powershell -NoProfile -ExecutionPolicy Bypass -File $env:TEMP\setup-keys.ps1
> Remove-Item $env:TEMP\setup-keys.ps1
> ```
>
> When it's done, run `. $PROFILE` or open a new PowerShell window."

### Windows (cmd)

> "PowerShell is the easier path. If you must use cmd, set keys with `setx`:
>
> ```
> setx SEATS_AERO_API_KEY \"your-key-here\"
> setx DUFFEL_API_KEY_LIVE \"your-key-here\"
> ```
>
> Open a new cmd window for the variables to take effect. Note that `setx` writes to the registry permanently."

### 1Password users

> "If you keep secrets in 1Password, you can use `op run` to resolve them at launch instead of writing to your shell rc. The toolkit has an `.env.example` that uses `op://` references. See https://developer.1password.com/docs/cli/secrets-environment-variables/ for the syntax. Then launch as: `op run --env-file=.env -- claude`."

**Don't ever offer to collect API keys via chat input.** If the user explicitly insists on pasting in chat, refuse politely and explain that the script is the safe path: keys typed into chat get retained in terminal scrollback, local session logs, and remote API logs. The script avoids all three.

## Step 4: Show sample prompts

After setup (or now, if keys are already set), show 3-4 prompts scaled to what they have configured. Re-detect first to confirm.

**No keys set:**
- "Find me a cheap nonstop flight from NYC to London next month."
- "What hotels are near the Eiffel Tower under $400/night?"
- "How do I get from Bergen to Oslo by train?" (if they're in Scandinavia)

**With Seats.aero:**
- "Plan a 10-day Scandinavia trip in August on points."
- "Cheapest business class to Tokyo for two in March."
- "Find me one outsized redemption I'm not using."

**With AwardWallet:**
- "Show me my points balances and which programs are about to expire."
- "Which transfer bonuses are active right now and worth using?"

End with a declarative statement (NOT a question, per the system prompt's PRE-OUTPUT GATE):

> "You're set. Type `/travel-hacker:plan-trip` to start a guided trip plan, or describe a trip in plain English."

## Don't do this

- **Never prompt for API keys in chat.** Always direct to `setup-keys.sh` or `setup-keys.ps1`. Chat input gets logged in too many places.
- **Never print API key values back to the user.** Not in confirmations, not in previews, not anywhere.
- **Never write secrets to `/tmp` or other ephemeral paths.** The setup-keys script uses the user's shell rc with backup.
- **Never offer "I'll print the export lines for you to paste."** That puts secrets in chat.
- **Don't end with action-offer questions** ("Want me to..."). The system prompt's PRE-OUTPUT GATE bans them.
- **Don't lecture about points/miles concepts.** Help them try one thing in the next 30 seconds.
- **Don't be apologetic about missing keys.** Frame as "here's what we can do with what you have."

## Tone

Concise, friendly, direct. Get them from "what do I have?" to "here's the script to run" in under a minute.

## Edge cases

- **User has keys in their shell session but not in their rc:** Note that they're set in the current process but won't survive. Suggest the setup script.
- **User uses 1Password:** Mention `op run --env-file=.env -- claude` as the alternative.
- **User on Windows asks about WSL/Git Bash:** Tell them to use the macOS/Linux instructions, not the PowerShell ones. The bash script works the same way under WSL.
- **User asks "can't you just collect the keys from me directly?"**: Refuse. Explain why (chat logs). Point them at the script. If they really insist, point them at the [README manual setup section](https://github.com/borski/travel-hacking-toolkit#manual-setup-if-youd-rather-not-use-the-skill) so at least the keys never enter the chat at all.
