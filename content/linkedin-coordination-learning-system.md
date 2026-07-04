We stopped building protocols. We started building the game that learns which protocols to play.

CE AGENTS has 53 coordination protocols and 56 AI agents. Until this week, every run started from scratch. The system had zero memory of what worked.

Now it learns. Every run records what happened, scores the output, and feeds it back. After enough data, the system knows which protocol performs best for which type of problem — and starts recommending configurations before you ask.

But the learning layer is just the foundation.

The real bet: agents that coordinate themselves. No predetermined turn order. No scripted roles. A conversation environment with hard boundaries where agents decide who speaks, what to contribute, when to challenge, and when to declare the work done.

We shipped the full architecture this week. 2,500 lines. 67 tests. Zero modifications to the existing production system. Feature-flagged so we can kill it with one env var if it doesn't earn its keep.

I wrote up the full engineering spec, the compression thesis behind it, and what the falsification conditions look like if we're wrong.

[Link to Substack]

#MultiAgentAI #CoordinationScience #BuildingInPublic
