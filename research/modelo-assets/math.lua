-- math.lua — pandoc Lua filter for the /modelo/ pages.
--
-- 1. Renders the article's code-span pseudo-math as real math (`v_f =
--    flatEqSpeed(P_flat)` → MathML via --mathml), translating the unicode
--    notation (α, ε, h₊, ², ·, ≈ …) to TeX and wrapping multi-letter
--    identifiers in \mathrm{}. The markdown source stays untouched.
-- 2. Converts the mathy fenced blocks of §1 (no language class, every line
--    mathy) to display math; language-tagged blocks (the ```js v2Edge
--    listing) stay code.
-- 3. Inlines the figs/*.svg images as <figure class="fig"> so CSS/JS can
--    make the data points interactive and the lightbox can zoom losslessly.
--
-- Classification is conservative: when in doubt, a span stays code.

-- ---------------------------------------------------------------- keep list
local KEEP = {}
for _, s in ipairs({
  "cf", "off", "zero", "reverse", "record", "auto", "pedalhidro", "origin",
  "v2Edge", "epsFromFIT", "epsGeom", "legE", "ode45", "flatEqSpeed",
  "compare", "censo_compare", "eps_hypothesis", "eps_sp_test", "time_compare",
  "ppaz_inventory", "ppaz_compare", "jaam_inventory", "jaam_compare",
  "danlessa_inventory", "danlessa_compare", "param_fit", "cda_estimate",
  "regime_compare", "verify_v2edge_clamp", "igc_resolution_test",
  "goal_calibration", "scale_trio", "bootstrap_ci",
  "regimeComponents", "regimeTotals", "approxComponents", "r0Champion",
  "TourShape", "aRoll", "aAero", "abRatio", "epsOffset", "climbThr", "beta",
}) do KEEP[s] = true end

local EXTS = { mjs=1, py=1, md=1, js=1, html=1, csv=1, ttl=1, tif=1, xlsx=1,
  gpx=1, fit=1, svg=1, json=1, pdf=1, cff=1, sh=1, lua=1, css=1, txt=1, xml=1 }

-- ------------------------------------------------------------- symbol table
local SYM = {
  {"₀₁", "_{01}"},  -- clamp₀₁: merge before the single-subscript maps below
  {"·", "\\cdot "}, {"≈", "\\approx "}, {"≥", "\\ge "}, {"≤", "\\le "},
  {"∈", "\\in "}, {"±", "\\pm "}, {"×", "\\times "}, {"−", "-"}, {"–", "-"},
  {"⇒", "\\Rightarrow "}, {"↔", "\\leftrightarrow "}, {"→", "\\to "},
  {"∫", "\\int "}, {"Σ", "\\Sigma "}, {"∑", "\\Sigma "}, {"∞", "\\infty "},
  {"∝", "\\propto "}, {"½", "\\tfrac{1}{2}"}, {"°", "^{\\circ}"},
  {"…", "\\dots "}, {"≠", "\\ne "}, {"≡", "\\equiv "}, {"≪", "\\ll "},
  {"₊", "_{+}"}, {"₋", "_{-}"}, {"₀", "_{0}"}, {"₁", "_{1}"}, {"₂", "_{2}"},
  {"₌", "_{=}"}, {"²", "^{2}"}, {"³", "^{3}"}, {"¹", "^{1}"}, {"⁻", "^{-}"},
  {"α", "\\alpha "}, {"β", "\\beta "}, {"γ", "\\gamma "}, {"δ", "\\delta "},
  {"ε", "\\epsilon "}, {"η", "\\eta "}, {"θ", "\\theta "}, {"κ", "\\kappa "},
  {"λ", "\\lambda "}, {"μ", "\\mu "}, {"ν", "\\nu "}, {"ρ", "\\rho "},
  {"σ", "\\sigma "}, {"τ", "\\tau "}, {"φ", "\\phi "}, {"ω", "\\omega "},
  {"Δ", "\\Delta "}, {"Ω", "\\Omega "},
}

local FN = { min="\\min", max="\\max", cos="\\cos", sin="\\sin", tan="\\tan",
  ln="\\ln", log="\\log", exp="\\exp" }

local MARKERS = { "·","≈","≥","≤","∈","±","×","−","⇒","↔","∫","Σ","√","∞",
  "∝","½","°","…","≠","≡","α","β","γ","δ","ε","η","θ","κ","λ","μ","ν","ρ",
  "σ","τ","φ","ω","Δ","Ω","₊","₋","₀","₁","₂","₌","²","³","¹","⁻",
  "=","<",">","^","%","|","*","(","/","+", "\204\132" }

-- --------------------------------------------------------------- classifier
local function is_math(s)
  if s == "" or s:find("[`'\"\\@#&]") then return false end
  if s:match("^%-") or s:match("^<") then return false end
  if s:find("//") or s:match("^[%w_%-%./]+/$") then return false end
  local ext = s:match("%.(%a+)$")
  if ext and EXTS[ext:lower()] then return false end
  if s:match("^[A-Za-z][%w%.]*%(%s*%)$") then return false end -- canonical()
  if s:match("_%*$") then return false end                     -- ppaz_*
  if KEEP[s] then return false end
  for _, m in ipairs(MARKERS) do
    if s:find(m, 1, true) then return true end
  end
  if s:match("^[%d%s%.,+%-]+$") then return true end           -- bare number
  if s:match("^[A-Za-z]$") then return true end                -- single var
  -- v_f, C_rr, k_smooth: 1–2-letter head + simple subscript word
  if s:match("^[A-Za-z][A-Za-z0-9]?_[A-Za-z0-9]+$") then return true end
  return false
end

-- ------------------------------------------------------------ TeX converter
local function to_tex(s)
  local stash_t = {}
  local function stash(tex)
    stash_t[#stash_t + 1] = tex
    return "\7" .. #stash_t .. "\7"
  end
  -- decimal commas (pt-BR): 0,20 → 0{,}20 so TeX adds no space
  s = s:gsub("(%d),(%d)", function(a, b) return a .. stash("{,}") .. b end)
  -- alignment gaps in fenced blocks
  s = s:gsub("   +", function() return stash(" \\qquad ") end)
  -- literal braces and percent
  s = s:gsub("[{}]", function(b) return stash("\\" .. b) end)
  s = s:gsub("%%", function() return stash("\\%") end)
  -- combining macron: s̄ → \bar{s} (any single UTF-8 char + U+0304)
  s = s:gsub("([^\128-\191][\128-\191]*)\204\132",
    function(c) return stash("\\bar{") .. c .. stash("}") end)
  -- ^(x) → ^{x} and √(x) → \sqrt{x}
  s = s:gsub("%^%(([^()]*)%)", function(x) return stash("^{") .. x .. stash("}") end)
  s = s:gsub("√%(([^()]*)%)", function(x) return stash("\\sqrt{") .. x .. stash("}") end)
  s = s:gsub("√", function() return stash("\\sqrt ") end)
  -- clamp_[0,1] → clamp_{[0,1]}
  s = s:gsub("_%[([^%]]*)%]", function(x) return stash("_{[") .. x .. stash("]}") end)
  -- subscripted words: _flat → _{\mathrm{flat}}, _f stays
  s = s:gsub("_([A-Za-z][A-Za-z0-9]*)", function(w)
    if #w == 1 then return "_" .. w end
    return stash("_{\\mathrm{" .. w .. "}}")
  end)
  -- remaining identifier runs: single letters stay variables, functions map,
  -- multi-letter names go upright
  s = s:gsub("[A-Za-z][A-Za-z0-9]*", function(w)
    if #w == 1 then return w end
    if FN[w] then return stash(FN[w] .. " ") end
    if w == "clamp" then return stash("\\mathrm{clamp}") end
    return stash("\\mathrm{" .. w .. "}")
  end)
  -- x* → x^{*}
  s = s:gsub("%*", function() return stash("^{*}") end)
  -- unicode symbols and greek
  for _, kv in ipairs(SYM) do
    s = s:gsub(kv[1], function() return stash(kv[2]) end)
  end
  -- restore
  s = s:gsub("\7(%d+)\7", function(i) return stash_t[tonumber(i)] end)
  return s
end

-- ------------------------------------------------------------------ filters
function Code(el)
  if is_math(el.text) then
    return pandoc.Math("InlineMath", to_tex(el.text))
  end
end

function CodeBlock(el)
  if #el.classes > 0 then return nil end -- language-tagged: real code
  local lines, all_math = {}, true
  for line in (el.text .. "\n"):gmatch("([^\n]*)\n") do
    if line:match("%S") then
      if not is_math(line) then all_math = false end
      lines[#lines + 1] = line
    end
  end
  if not all_math or #lines == 0 then return nil end
  local tex = {}
  for _, l in ipairs(lines) do tex[#tex + 1] = to_tex(l) end
  return pandoc.Para{ pandoc.Math("DisplayMath",
    "\\begin{gathered}" .. table.concat(tex, " \\\\ ") .. "\\end{gathered}") }
end

function Para(el)
  if #el.content == 1 and el.content[1].t == "Image" then
    local src = el.content[1].src
    if src:match("^figs/.*%.svg$") then
      local f = io.open(src, "r")
      if f then
        local svg = f:read("*a"); f:close()
        svg = svg:gsub("^.-<svg", "<svg", 1)
        return pandoc.RawBlock("html",
          '<figure class="fig" tabindex="0">' .. svg .. '</figure>')
      end
    end
  end
end
