cask "mindroom-chat" do
  version "0"
  sha256 "0000000000000000000000000000000000000000000000000000000000000000"

  url "https://github.com/mindroom-ai/mindroom-chat/releases/download/v#{version}/MindRoom-Chat.dmg"
  name "MindRoom Chat"
  desc "Matrix chat client for MindRoom AI agents"
  homepage "https://github.com/mindroom-ai/mindroom-chat"

  livecheck do
    url :url
    strategy :github_latest
  end

  depends_on macos: :ventura

  app "MindRoom Chat.app"

  zap trash: [
    "~/Library/Caches/chat.mindroom.app",
    "~/Library/Preferences/chat.mindroom.app.plist",
    "~/Library/WebKit/chat.mindroom.app",
  ]
end
