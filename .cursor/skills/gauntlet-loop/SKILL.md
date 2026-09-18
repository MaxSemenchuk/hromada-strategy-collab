---
name: gauntlet-loop
description: Turns any goal into one short, paste-ready gauntlet-loop prompt — a real quality bar, builder/critic pairs, blind compare, loop until it wins. Triggers on gauntlet-loop, gauntlet this, make a gauntlet prompt, loop until it beats X.
---

# Gauntlet Loop

Upstream: [robonuggets/gauntlet-loop](https://github.com/robonuggets/gauntlet-loop) (CC BY 4.0). Technique by Matt Shumer.

The user gives a goal. You give back ONE short prompt they can paste into a fresh agent session.

You are not doing the work. You are writing the prompt that makes another agent grind on the work until it beats a real reference.

## Flow

1. **Read the goal.** One line restatement in your head, not on screen.
2. **Set the bar.** If the user supplied a reference, use it. If not, offer **2 or 3 candidate bars**, one line each, and stop. Wait for their pick. Do not write the prompt yet.
3. **Write the prompt.** One block, paste-ready, no preamble, no headings inside it, no narration after it.
4. **Offer to run it.** One flat line under the prompt: "I can run this here." Not a question.

If they say run it, you become the lead agent and follow the prompt you just wrote.

## The bar is the whole trick

A bar has to pass three tests:

- **Named.** A specific thing, not a category.
- **Fetchable.** The critic can screenshot it, read it, run it, or open it.
- **Comparable.** Both can sit side by side and a judge can pick one.

When you propose bars, prefer the hardest one the agent can genuinely reach.

## Prompt template

Adapt the wording every time. Fill the brackets, keep it short, keep the last line.

```
Build [GOAL].

The bar is [BAR]. Get the real thing first and compare against it directly, not against a description of it.

Break this into the smallest pieces that can be improved and judged on their own. For each piece, fan out a builder and a separate critic with fresh context. The critic inspects the actual output, puts it next to the bar blind with the labels stripped, says which one is better, and names the single biggest remaining gap. Then it goes back to the builder.

The critic should be a harsh critic. Praise is not useful. If ours does not win, it keeps going.

Keep looping on each piece until the critic picks ours blind. Do not stop before that. Run the builders and critics as parallel subagents.

Keep a live progress page updating as the work evolves so I can watch it.
```

Bake the bar in as a concrete, fetchable thing. Add a budget line only if the user named one. No architecture, file layout, round count, or stack unless the user demanded it.
