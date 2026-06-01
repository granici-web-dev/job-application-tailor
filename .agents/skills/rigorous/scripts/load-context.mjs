#!/usr/bin/env node
/**
 * Loads PRINCIPLES.md, STACK.md, TESTING.md from the project's context dir.
 * Lookup order: $RIGOROUS_CONTEXT_DIR → cwd → .agents/context → docs.
 *
 * Output: a single JSON object on stdout. Always parse the whole thing — don't
 * pipe through head/tail/grep/jq.
 */
import { readFileSync, statSync } from "node:fs";
import { resolve, join, isAbsolute } from "node:path";

const FILES = ["PRINCIPLES.md", "STACK.md", "TESTING.md"];
// Some teams write CODE_STANDARDS instead of PRINCIPLES; accept aliases.
const ALIASES = {
  "PRINCIPLES.md": ["PRINCIPLES.md", "ENGINEERING.md", "CODE_STANDARDS.md"],
  "STACK.md": ["STACK.md", "TECH_STACK.md"],
  "TESTING.md": ["TESTING.md", "TEST_STRATEGY.md"],
};

function exists(p) {
  try {
    return statSync(p).isFile();
  } catch {
    return false;
  }
}

function readCaseInsensitive(dir, names) {
  for (const name of names) {
    for (const variant of [name, name.toLowerCase(), name.toUpperCase()]) {
      const p = join(dir, variant);
      if (exists(p)) {
        return { path: p, content: readFileSync(p, "utf8") };
      }
    }
  }
  return null;
}

function pickContextDir(cwd) {
  const env = process.env.RIGOROUS_CONTEXT_DIR;
  if (env) {
    return isAbsolute(env) ? env : resolve(cwd, env);
  }
  // Search root, then .agents/context, then docs/. First with PRINCIPLES (or alias) wins.
  for (const sub of ["", ".agents/context", "docs"]) {
    const dir = sub ? resolve(cwd, sub) : cwd;
    if (readCaseInsensitive(dir, ALIASES["PRINCIPLES.md"])) {
      return dir;
    }
  }
  return cwd; // default to cwd even if nothing found yet
}

function isPlaceholder(content) {
  if (!content) return true;
  const stripped = content.replace(/<!--[\s\S]*?-->/g, "").trim();
  if (stripped.length < 100) return true;
  if (/\[TODO\]/i.test(stripped) && stripped.length < 400) return true;
  return false;
}

const cwd = process.cwd();
const contextDir = pickContextDir(cwd);

const out = {
  contextDir,
  cwd,
  files: {},
  summary: { found: [], missing: [], placeholder: [] },
};

for (const canonical of FILES) {
  const aliases = ALIASES[canonical];
  const found = readCaseInsensitive(contextDir, aliases);
  if (!found) {
    out.files[canonical] = { exists: false, path: null, content: null, placeholder: false };
    out.summary.missing.push(canonical);
    continue;
  }
  const placeholder = isPlaceholder(found.content);
  out.files[canonical] = {
    exists: true,
    path: found.path,
    content: found.content,
    placeholder,
  };
  out.summary.found.push(canonical);
  if (placeholder) out.summary.placeholder.push(canonical);
}

out.ok = out.summary.found.includes("PRINCIPLES.md") &&
         !out.summary.placeholder.includes("PRINCIPLES.md");

process.stdout.write(JSON.stringify(out, null, 2));
process.stdout.write("\n");
