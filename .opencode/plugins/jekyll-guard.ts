// jekyll-guard: project hooks for mingchen-site (personal Jekyll site).
//
// - Block accidental edits to build-generated paths (with a clear message explaining the right fix).
// - Cap shell timeouts so a hung `jekyll build/serve` cannot hold the agent.
//
// OpenCode auto-loads files under .opencode/plugins/, so no extra registration is needed.
// Written as a plain object (no imports), like the system plugin, to stay light and reliably loadable.

const GENERATED_SEGMENTS = ["_site", ".jekyll-cache", ".sass-cache", "vendor", ".bundle"]
const GENERATED_FILES = ["Gemfile.lock"]

function isGeneratedPath(resource) {
  if (typeof resource !== "string" || resource.length === 0) return false
  const segments = resource.replace(/\\/g, "/").split("/").filter(Boolean)
  if (segments.length === 0) return false
  if (segments.some((seg) => GENERATED_SEGMENTS.includes(seg))) return true
  return GENERATED_FILES.includes(segments[segments.length - 1])
}

export default {
  id: "jekyll-guard",
  async setup(ctx) {
    // Runs after the permission rules in the config are evaluated, before the action runs.
    // Only narrows allow/ask decisions; keep any deny already present in the config.
    await ctx.permission.hook("evaluate", (event) => {
      if (event.action !== "edit") return
      const hit = (event.resources || []).filter(isGeneratedPath)
      if (hit.length === 0) return
      event.effect = "deny"
      event.message =
        "Build-generated path, do not edit by hand: " + hit.join(", ") + ". " +
        "Run `bundle exec jekyll build` to regenerate output, or `bundle install`/`bundle update` instead of editing Gemfile.lock."
    })

    // Avoid hung shells (heavy jekyll serve/build) holding the agent too long.
    await ctx.shell.hook("create.before", (event) => {
      const MAX_TIMEOUT_MS = 300000
      if (typeof event.timeout === "number" && event.timeout > MAX_TIMEOUT_MS) {
        event.timeout = MAX_TIMEOUT_MS
      }
    })
  },
}
