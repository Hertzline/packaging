# Homebrew cask draft for Hertzline (HZ-051).
# Draft only -- do not submit to Homebrew/homebrew-cask without owner approval.
# Replace PLACEHOLDER sha256 and confirm url asset name before any PR.
cask "hertzline" do
  version "0.0.0"
  sha256 "PLACEHOLDER_REPLACE_WITH_RELEASE_SHA256"

  url "https://github.com/Hertzline/app/releases/download/v#{version}/Hertzline_#{version}_aarch64.dmg"
  name "Hertzline"
  desc "Measured, reversible game and desktop smoothing"
  homepage "https://github.com/Hertzline"

  depends_on macos: ">= :ventura"

  app "Hertzline.app"

  # zap is cleanup only; privileged restore is hertzline-helper restore_all (AC-7.3).
  zap trash: [
    "~/Library/Application Support/com.hertzline.desktop",
    "~/Library/Caches/com.hertzline.desktop",
    "~/Library/Preferences/com.hertzline.desktop.plist",
  ]
end
