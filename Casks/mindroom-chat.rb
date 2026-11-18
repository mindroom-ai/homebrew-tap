cask "mindroom-chat" do
  version "2026.11.285"
  sha256 "25c233b233ba259ffaced34c1f5f93e35164d467a393f8aad398a9a3fe0397eb"

  url "https://github.com/mindroom-ai/mindroom-chat/releases/download/v#{version}/MindRoom.dmg"
  name "MindRoom Chat"
  desc "Matrix chat client for MindRoom AI agents"
  homepage "https://github.com/mindroom-ai/mindroom-chat"

  # The newest release that has the DMG, as the updater picks it: a release gets its DMG from a
  # macOS build that ends after it is published, and none when that build fails.
  livecheck do
    url :url
    strategy :github_releases do |json, regex|
      json.map do |release|
        next if release["draft"] || release["prerelease"]
        next unless release["assets"]&.any? { |asset| asset["name"] == "MindRoom.dmg" }

        release["tag_name"]&.[](regex, 1)
      end
    end
  end

  depends_on macos: :ventura

  # The DMG holds MindRoom.app, the name the MindRoom cask's menu bar app also installs as.
  app "MindRoom.app", target: "MindRoom Chat.app"

  # Leave ~/Library/Containers/chat.mindroom.app: it belongs to the App Store app.
  zap trash: [
    "~/Library/Caches/chat.mindroom.app",
    "~/Library/HTTPStorages/chat.mindroom.app",
    "~/Library/HTTPStorages/chat.mindroom.app.binarycookies",
    "~/Library/Preferences/chat.mindroom.app.plist",
    "~/Library/Saved Application State/chat.mindroom.app~iosmac.savedState",
    "~/Library/WebKit/chat.mindroom.app",
  ]
end
