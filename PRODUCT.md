# Product

## Register

product

## Users

One person: the job seeker who owns this machine, using the tool during an active job hunt. They work attentively, one application at a time, in a focused session at a desk. They are technical enough to run Docker and read Markdown, and they care about the quality of what goes out under their name. They are not a customer to be onboarded or sold to; they are the operator and the only user.

## Product Purpose

Take a job posting, adapt a master CV and a cover letter to it (ATS-correct, in the posting's language), and produce two downloadable PDFs plus a tracked row in a shared spreadsheet. The interface exists so the user can paste a link, watch the pipeline run, and read and trust the result before it reaches a real employer. Success is a generated CV and letter the user is confident enough to send without rewriting, and a history they can keep straight. The CLI handles batch and testing; the UI owns the careful single-application path.

## Brand Personality

Precise, calm, trustworthy. The voice is plain and exact, never salesy or chipper. The interface behaves like a competent tool that won't make mistakes with something that matters: legible, predictable, quiet. Confidence comes from clarity, not decoration.

## Anti-references

- Busy SaaS marketing energy: hero gradients, decorative card grids, eyebrow kickers, "supercharge your job search" copy. This is a tool, not a product being sold.
- Gradient text, glassmorphism, drop-shadowed cards, over-rounded everything: visual noise that undercuts the "trustworthy" read.
- Consumer-app gamification (streaks, confetti, motivational nudges). Job hunting is stressful enough; the tool stays out of the way.
- Anything that obscures where the content came from. The UI must never imply the documents are invented; they are grounded in the user's own master CV.

## Design Principles

- **Review is the primary action.** The output is going to an employer. The interface is built to let the user read, compare against the source, and verify the generated CV and letter before downloading, not just to fetch files fast.
- **Never imply fabrication.** The tool only reformulates real experience from the master CV. The UI should make provenance legible and never present generated content as if it appeared from nowhere.
- **The tool disappears into the task.** Earned familiarity over novelty. Standard affordances, consistent component vocabulary, nothing the user has to learn. Linear/Raycast/Stripe-grade restraint.
- **Quiet under pressure.** This is used during a stressful stretch. The surface stays calm and readable; no loud color, no orchestrated motion, no urgency theater.
- **One application, done well.** Optimize the single attentive flow first; the history table and status tracking support it. Batch lives in the CLI.

## Accessibility & Inclusion

- WCAG AA contrast throughout: body text ≥4.5:1, large text ≥3:1. Holds for placeholder and muted text too.
- Full keyboard operation: every action reachable and operable without a mouse, with visible focus states. Fits the precise, technical workflow.
- Reduced-motion support is non-optional: every animation has a `prefers-reduced-motion` alternative.
