// jekyll-guard: project hooks cho mingchen-site (site Jekyll cá nhân).
//
// - Chặn sửa nhầm các đường dẫn do build sinh ra (kèm lời nhắn rõ cách làm đúng).
// - Giới hạn timeout của shell để `jekyll build/serve` bị treo không giữ agent.
//
// OpenCode tự load file dưới .opencode/plugins/ nên không cần đăng ký thêm.
// Viết dạng object thuần (không import) giống plugin hệ thống để nhẹ và chắc chắn load.

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
    // Chạy sau khi rule permissions trong config được tính, trước khi action chạy.
    // Chỉ can thiệp quyết định allow/ask; deny có sẵn trong config thì giữ nguyên.
    await ctx.permission.hook("evaluate", (event) => {
      if (event.action !== "edit") return
      const hit = (event.resources || []).filter(isGeneratedPath)
      if (hit.length === 0) return
      event.effect = "deny"
      event.message =
        "Đường dẫn do build sinh ra, không sửa tay: " + hit.join(", ") + ". " +
        "Chạy `bundle exec jekyll build` để tạo lại output, hoặc `bundle install`/`bundle update` thay vì sửa Gemfile.lock."
    })

    // Tránh shell treo (jekyll serve/build nặng) giữ agent quá lâu.
    await ctx.shell.hook("create.before", (event) => {
      const MAX_TIMEOUT_MS = 300000
      if (typeof event.timeout === "number" && event.timeout > MAX_TIMEOUT_MS) {
        event.timeout = MAX_TIMEOUT_MS
      }
    })
  },
}
