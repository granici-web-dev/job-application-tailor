#!/usr/bin/env node
/**
 * Create or remove a standalone shortcut for a rigorous sub-command.
 *
 * Usage:
 *   node pin.mjs pin <command>
 *   node pin.mjs unpin <command>
 *
 * Writes a tiny skill stub at ~/.claude/skills/<command>/SKILL.md that
 * delegates to /rigorous <command>, so the user can type /<command>
 * directly.
 */
import { mkdirSync, writeFileSync, existsSync, rmSync } from "node:fs";
import { join } from "node:path";
import { homedir } from "node:os";
import { readFileSync } from "node:fs";

const VALID = new Set([
  "teach", "document", "shape", "craft", "tdd",
  "critique", "audit", "architect",
  "simplify", "harden", "refactor",
  "debug", "optimize",
]);

const [, , action, name] = process.argv;

if (!action || !name) {
  console.error("usage: pin.mjs <pin|unpin> <command>");
  process.exit(2);
}

if (!VALID.has(name)) {
  console.error(`unknown rigorous sub-command: ${name}`);
  console.error(`valid: ${Array.from(VALID).join(", ")}`);
  process.exit(2);
}

const skillsDir = join(homedir(), ".claude", "skills");
const targetDir = join(skillsDir, name);
const targetFile = join(targetDir, "SKILL.md");

if (action === "unpin") {
  if (!existsSync(targetDir)) {
    console.log(`/${name} not pinned (nothing to remove)`);
    process.exit(0);
  }
  rmSync(targetDir, { recursive: true, force: true });
  console.log(`unpinned: /${name}`);
  process.exit(0);
}

if (action !== "pin") {
  console.error(`unknown action: ${action} (expected pin|unpin)`);
  process.exit(2);
}

// Resolve the metadata for description / argumentHint.
const metaPath = new URL("./command-metadata.json", import.meta.url);
const meta = JSON.parse(readFileSync(metaPath, "utf8"));
const cmd = meta[name];
if (!cmd) {
  console.error(`metadata missing for ${name}`);
  process.exit(2);
}

mkdirSync(targetDir, { recursive: true });

const frontmatter = [
  "---",
  `name: ${name}`,
  `description: "${cmd.description}"`,
  `argument-hint: "${cmd.argumentHint || ""}"`,
  "user-invocable: true",
  "---",
  "",
  `Shortcut for \`/rigorous ${name}\`. Loads the rigorous skill and runs the \`${name}\` command with the provided argument.`,
  "",
  "## Routing",
  "",
  `Invoke the \`rigorous\` skill with command \`${name}\` and pass through the user's argument verbatim.`,
  "",
  "Setup gates from the rigorous skill apply (context loading, principles file, etc.). Do not skip them.",
  "",
].join("\n");

writeFileSync(targetFile, frontmatter, "utf8");
console.log(`pinned: /${name} (delegates to /rigorous ${name})`);
