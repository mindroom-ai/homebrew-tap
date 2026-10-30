cask "mindroom-chat" do
  version "4.12.6-mindroom.274"
  sha256 "ad401944e48a9044caad3cd71e6b0ec3b6ba678258def88a83ba2c3da23b0e5d"

  url "https://github.com/mindroom-ai/mindroom-chat/releases/download/v#{version}/MindRoom-Chat.dmg"
  name "MindRoom Chat"
  desc "Matrix chat client for MindRoom AI agents"
  homepage "https://github.com/mindroom-ai/mindroom-chat"

  # Keep the -mindroom.N suffix; the default regex stops at 4.12.6.
  livecheck do
    url :url
    regex(/^v?(\d+(?:\.\d+)+-mindroom\.\d+)$/i)
    strategy :github_latest
  end

  depends_on macos: :ventura

  app "MindRoom Chat.app"

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
