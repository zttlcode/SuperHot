// Run against a dedicated QA instance; never against a server containing user data.
const { chromium } = require("playwright");
const fs = require("fs");
const path = require("path");
const assert = require("assert/strict");
const base = process.env.BASE_URL || "http://127.0.0.1:8766";
const output = path.resolve(__dirname, "../../.runtime/browser-screenshots");
fs.mkdirSync(output, { recursive: true });
(async () => {
  const browser = await chromium.launch({
    headless: true,
    ...(process.env.CHROME_PATH
      ? { executablePath: process.env.CHROME_PATH }
      : process.platform === "win32"
        ? {
            executablePath:
              "C:/Program Files/Google/Chrome/Application/chrome.exe",
          }
        : {}),
  });
  const page = await browser.newPage({
    viewport: { width: 1440, height: 1000 },
    acceptDownloads: true,
    reducedMotion: "reduce",
  });
  const errors = [];
  page.on("pageerror", (error) => errors.push(error.message));
  try {
    await page.goto(base);
    await page.getByRole("heading", { name: /关注值得关注的/ }).waitFor();
    await page.waitForFunction(
      () =>
        getComputedStyle(document.querySelector(".hero-copy")).opacity === "1",
    );
    await page.screenshot({
      path: path.join(output, "home.png"),
      fullPage: true,
    });
    await page.getByRole("button", { name: "开始我的监控" }).click();
    await page.getByLabel("怎么称呼你").fill("QA Operator");
    await page
      .getByLabel("邮箱", { exact: true })
      .fill("qa-" + Date.now() + "@superhot.test");
    await page
      .getByLabel("密码", { exact: true })
      .fill("qa-private-password-123");
    await page
      .getByLabel("团队邀请码")
      .fill(process.env.TEST_INVITE_CODE || "browser-qa-invitation");
    await page.getByRole("button", { name: "创建账号", exact: true }).click();
    await page
      .getByRole("heading", { name: "下一条好内容，从一个关注开始。" })
      .waitFor();
    await page
      .getByRole("button", { name: "设置 TikHub Key", exact: true })
      .click();
    await page
      .getByLabel("粘贴你的 TikHub API Key")
      .fill("ui-test-key-never-sent-to-tikhub");
    await page.getByRole("button", { name: "保存设置", exact: true }).click();
    await page.getByText("•••• khub", { exact: true }).waitFor();
    if (
      await page.getByRole("button", { name: "系统管理", exact: true }).count()
    ) {
      await page.getByRole("button", { name: "系统管理", exact: true }).click();
      await page.getByText("2.2.0", { exact: true }).waitFor();
      await page.route("**/api/admin/sdk?force=true", (route) =>
        route.fulfill({
          json: {
            current: "2.2.0",
            latest: "2.2.0",
            notes: "QA release notes",
            url: "https://github.com/TikHub/TikHub-API-Python-SDK/releases",
            checked_at: Date.now() / 1000,
            available: true,
            can_update: false,
            blocked: null,
          },
        }),
      );
      await page
        .getByRole("button", { name: "检查新版本", exact: true })
        .click();
      await page.getByText("Release notes", { exact: true }).waitFor();
      assert.equal(
        await page
          .getByRole("button", { name: "验证并更新", exact: true })
          .count(),
        0,
      );
    }
    const now = Date.now() / 1000;
    let monitors = [];
    let posts = [
      {
        id: "post-1",
        platform: "tiktok",
        platform_id: "12345678",
        monitor_id: "creator-1",
        text: "一条用于端到端验证的示例文案。",
        kind: "images",
        cover: "",
        share_url: "",
        published_at: now,
        found_at: now,
        is_new: true,
        read: false,
        asset_count: 1,
        assets: [
          {
            id: "image-1",
            kind: "image",
            order: 0,
            preview: "",
            downloadable: true,
          },
        ],
        post_type: "original",
        references: [],
        author: "QA Creator",
        username: "qa.creator",
      },
    ];
    // Only third-party-dependent UI paths are simulated. Authentication and Key persistence are real.
    let resolvedPlatform = "tiktok";
    const creators = {
      tiktok: { id: "creator-1", name: "QA Creator" },
      twitter: { id: "twitter-creator", name: "QA Twitter Creator" },
      douyin: { id: "douyin-creator", name: "QA Douyin Creator" },
    };
    await page.route("**/api/monitors/resolve", (route) => {
      const url = route.request().postDataJSON().url;
      resolvedPlatform = url.includes("douyin.com")
        ? "douyin"
        : url.includes("x.com")
          ? "twitter"
          : "tiktok";
      return route.fulfill({
        json: {
          resolution_id: "resolved-1",
          author: {
            platform: resolvedPlatform,
            nickname: creators[resolvedPlatform].name,
            username: "qa.creator",
            avatar: "",
          },
        },
      });
    });
    await page.route("**/api/monitors", async (route) => {
      if (route.request().method() === "POST") {
        const created = {
          id: creators[resolvedPlatform].id,
          platform: resolvedPlatform,
          author_id: "author-1",
          nickname: creators[resolvedPlatform].name,
          username: "qa.creator",
          avatar: "",
          source_url: "https://www.tiktok.com/@qa.creator",
          interval_hours: 2,
          enabled: true,
          next_check_at: now + 3600,
          last_success_at: now,
          last_attempt_at: now,
          baseline_at: now,
          state: "idle",
          last_error: null,
          created_at: now,
        };
        monitors.push(created);
        await route.fulfill({ status: 201, json: created });
      } else await route.fulfill({ json: monitors });
    });
    await page.route("**/api/monitors/creator-1", async (route) => {
      if (route.request().method() === "PATCH") {
        Object.assign(monitors[0], route.request().postDataJSON());
        await route.fulfill({ json: monitors[0] });
      } else {
        monitors = [];
        await route.fulfill({ json: { ok: true } });
      }
    });
    await page.route("**/api/monitors/creator-1/check", (route) =>
      route.fulfill({ json: { ok: true } }),
    );
    await page.route("**/api/posts?*", (route) => {
      const filter = new URL(route.request().url()).searchParams;
      const items = posts.filter(
        (post) =>
          (!filter.get("platform") ||
            post.platform === filter.get("platform")) &&
          (!filter.get("author") || post.monitor_id === filter.get("author")),
      );
      return route.fulfill({ json: { items, total: items.length, page: 1 } });
    });
    await page.route("**/api/posts/post-1/read", (route) => {
      posts[0].read = true;
      return route.fulfill({ json: { ok: true } });
    });
    await page.route("**/api/posts/post-1/assets/image-1/download", (route) =>
      route.fulfill({
        status: 200,
        headers: {
          "Content-Type": "image/png",
          "Content-Disposition": 'attachment; filename="qa-image.png"',
        },
        body: Buffer.from(
          "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aGMcAAAAASUVORK5CYII=",
          "base64",
        ),
      }),
    );
    await page.getByRole("button", { name: "监控对象", exact: true }).click();
    await page
      .getByRole("button", { name: "添加监控", exact: true })
      .first()
      .click();
    await page
      .getByLabel("TikTok、Twitter/X 或抖音主页、作品链接")
      .fill("https://www.tiktok.com/@qa.creator");
    await page.getByLabel("检查间隔（小时，1–168）").fill("2");
    await page.getByRole("button", { name: "识别作者", exact: true }).click();
    await page.getByRole("button", { name: "确认作者，开始监控" }).click();
    await page.getByText("QA Creator", { exact: true }).first().waitFor();
    await page.getByRole("button", { name: "暂停 QA Creator" }).click();
    await page.getByText("已暂停", { exact: true }).waitFor();
    await page.getByRole("button", { name: "恢复 QA Creator" }).click();
    await page.getByText("监控中", { exact: true }).waitFor();
    await page.getByRole("button", { name: "立即检查 QA Creator" }).click();
    await page.getByPlaceholder("搜索作者或用户名").fill("does-not-exist");
    await page.getByRole("heading", { name: "没有匹配的结果" }).waitFor();
    await page.getByPlaceholder("搜索作者或用户名").fill("");
    await page.screenshot({
      path: path.join(output, "watchlist.png"),
      fullPage: true,
    });
    await page.getByRole("button", { name: "更新内容", exact: true }).click();
    await page.getByText("一条用于端到端验证的示例文案。").click();
    await page.getByRole("dialog", { name: "作品详情" }).waitFor();
    const download = page.waitForEvent("download");
    await page.getByRole("button", { name: "下载图片 1", exact: true }).click();
    assert.equal((await download).suggestedFilename(), "qa-image.png");
    await page.keyboard.press("Escape");
    await page.getByRole("dialog").waitFor({ state: "hidden" });
    await page.getByRole("button", { name: "监控对象", exact: true }).click();
    await page.getByRole("button", { name: "添加监控", exact: true }).click();
    await page
      .getByLabel("TikTok、Twitter/X 或抖音主页、作品链接")
      .fill("https://x.com/sample_creator");
    await page.getByRole("button", { name: "识别作者", exact: true }).click();
    await page
      .getByText("Twitter/X 当前监控原创和引用帖，不包含回复及纯转发。", {
        exact: true,
      })
      .waitFor();
    await page.getByRole("button", { name: "确认作者，开始监控" }).click();
    await page.getByText("QA Twitter Creator", { exact: true }).waitFor();
    await page.getByLabel("平台", { exact: true }).selectOption("twitter");
    assert.equal(
      await page.getByText("QA Creator", { exact: true }).count(),
      0,
    );
    const twitterBase = {
      ...posts[0],
      platform: "twitter",
      monitor_id: "twitter-creator",
      author: "QA Twitter Creator",
      read: true,
      share_url: "https://x.com/sample_creator/status/1900000000000000001",
    };
    posts.push({
      ...twitterBase,
      id: "twitter-text",
      kind: "text",
      text: "纯文字 Twitter 帖子，支持换行。\n完整正文。",
      asset_count: 0,
      assets: [],
    });
    posts.push({
      ...twitterBase,
      id: "twitter-mixed",
      kind: "mixed",
      text: "Twitter 混合素材与引用内容。",
      post_type: "quote",
      references: [
        {
          kind: "quote",
          id: "99",
          username: "original_author",
          text: "引用作者的文字",
          url: "https://x.com/original_author/status/99",
        },
      ],
      asset_count: 4,
      assets: [
        {
          id: "photo-stable",
          kind: "image",
          order: 0,
          preview: "",
          downloadable: true,
        },
        {
          id: "video-stable",
          kind: "video",
          order: 1,
          preview: "",
          downloadable: true,
        },
        {
          id: "gif-stable",
          kind: "animated_gif",
          order: 2,
          preview: "",
          downloadable: true,
        },
        {
          id: "hls-only",
          kind: "video",
          order: 3,
          preview: "",
          downloadable: false,
        },
      ],
    });
    const requestedAssets = [];
    await page.route(
      "**/api/posts/twitter-mixed/assets/*/download",
      (route) => {
        const assetId = new URL(route.request().url()).pathname
          .split("/")
          .at(-2);
        requestedAssets.push(assetId);
        return route.fulfill({
          headers: {
            "Content-Type":
              assetId === "photo-stable" ? "image/png" : "video/mp4",
            "Content-Disposition": `attachment; filename="${assetId}.mp4"`,
          },
          body: Buffer.from("offline-media-fixture"),
        });
      },
    );
    await page.getByRole("button", { name: "更新内容", exact: true }).click();
    await page
      .getByText("纯文字 Twitter 帖子，支持换行。 完整正文。", { exact: true })
      .last()
      .click();
    await page.getByRole("dialog").waitFor();
    await page
      .getByText("纯文字作品，可使用上方按钮复制正文。", { exact: true })
      .waitFor();
    assert.equal(
      await page
        .getByRole("dialog")
        .getByRole("button", { name: /下载/ })
        .count(),
      0,
    );
    assert.equal(
      await page.getByRole("link", { name: "查看原作品" }).getAttribute("href"),
      twitterBase.share_url,
    );
    await page.keyboard.press("Escape");
    await page
      .getByText("Twitter 混合素材与引用内容。", { exact: true })
      .click();
    await page.getByText("引用作者的文字", { exact: true }).waitFor();
    for (const [label, assetId] of [
      ["下载图片 1", "photo-stable"],
      ["下载视频 2", "video-stable"],
      ["下载动图（MP4） 3", "gif-stable"],
    ]) {
      const saved = page.waitForEvent("download");
      await page.getByRole("button", { name: label, exact: true }).click();
      assert.equal((await saved).suggestedFilename(), assetId + ".mp4");
    }
    assert.deepEqual(requestedAssets, [
      "photo-stable",
      "video-stable",
      "gif-stable",
    ]);
    assert.ok(
      await page
        .getByRole("button", { name: "暂无可下载直链", exact: true })
        .isDisabled(),
    );
    await page.screenshot({
      path: path.join(output, "twitter-mixed-detail.png"),
      fullPage: true,
    });
    await page.keyboard.press("Escape");
    await page.getByRole("dialog").waitFor({ state: "hidden" });
    for (const width of [1440, 768, 390, 320]) {
      await page.setViewportSize({ width, height: 1000 });
      await page.evaluate(
        () =>
          new Promise((resolve) =>
            requestAnimationFrame(() => requestAnimationFrame(resolve)),
          ),
      );
      if (
        await page.evaluate(
          () => document.documentElement.scrollWidth > innerWidth + 1,
        )
      ) {
        console.log(
          "Twitter overflow",
          width,
          await page.evaluate(() =>
            Array.from(document.querySelectorAll("body *"))
              .filter(
                (element) =>
                  element.getBoundingClientRect().right > innerWidth + 1,
              )
              .map((element) => ({
                tag: element.tagName,
                cls: element.className?.toString(),
                width: element.getBoundingClientRect().width,
                right: element.getBoundingClientRect().right,
              }))
              .slice(0, 15),
          ),
        );
        await page.screenshot({
          path: path.join(output, "twitter-overflow.png"),
          fullPage: true,
        });
      }
      assert.ok(
        await page.evaluate(
          () => document.documentElement.scrollWidth <= innerWidth + 1,
        ),
        "Twitter feed overflow at " + width,
      );
    }
    await page.screenshot({
      path: path.join(output, "twitter-feed-mobile.png"),
      fullPage: true,
    });
    await page.setViewportSize({ width: 1440, height: 1000 });
    await page.getByRole("button", { name: "监控对象", exact: true }).click();
    await page.getByRole("button", { name: "添加监控", exact: true }).click();
    await page
      .getByLabel("TikTok、Twitter/X 或抖音主页、作品链接")
      .fill(
        "长按复制此条消息，打开抖音搜索，查看TA的更多作品。 https://v.douyin.com/sample/",
      );
    await page.getByRole("button", { name: "识别作者", exact: true }).click();
    await page.getByText("QA Douyin Creator", { exact: true }).waitFor();
    await page.getByRole("button", { name: "确认作者，开始监控" }).click();
    await page.getByRole("dialog").waitFor({ state: "hidden" });
    // Creation must clear the previous Twitter filter so the new author is visible.
    await page.getByText("QA Douyin Creator", { exact: true }).waitFor();
    await page.getByLabel("平台", { exact: true }).selectOption("douyin");
    assert.equal(
      await page.getByText("QA Twitter Creator", { exact: true }).count(),
      0,
    );
    assert.equal(
      await page.getByText("QA Creator", { exact: true }).count(),
      0,
    );
    const douyinBase = {
      ...twitterBase,
      platform: "douyin",
      monitor_id: "douyin-creator",
      author: "QA Douyin Creator",
    };
    posts.push({
      ...douyinBase,
      id: "douyin-video",
      platform_id: "1900000000000000300",
      text: "抖音视频下载验证。",
      kind: "video",
      share_url: "https://www.douyin.com/video/1900000000000000300",
      asset_count: 1,
      assets: [
        {
          id: "video",
          kind: "video",
          order: 0,
          preview: "",
          downloadable: true,
        },
      ],
    });
    posts.push({
      ...douyinBase,
      id: "douyin-gallery",
      platform_id: "1900000000000000301",
      text: "抖音图文下载验证。",
      kind: "images",
      share_url: "https://www.douyin.com/note/1900000000000000301",
      asset_count: 2,
      assets: [
        {
          id: "douyin-photo-1",
          kind: "image",
          order: 0,
          preview: "",
          downloadable: true,
        },
        {
          id: "douyin-photo-2",
          kind: "image",
          order: 1,
          preview: "",
          downloadable: true,
        },
      ],
    });
    const douyinAssets = [];
    await page.route("**/api/posts/douyin-*/assets/*/download", (route) => {
      const assetId = new URL(route.request().url()).pathname.split("/").at(-2);
      douyinAssets.push(assetId);
      const ext = assetId === "video" ? "mp4" : "webp";
      return route.fulfill({
        headers: {
          "Content-Type": assetId === "video" ? "video/mp4" : "image/webp",
          "Content-Disposition": `attachment; filename="${assetId}.${ext}"`,
        },
        body: Buffer.from("offline-douyin-media-fixture"),
      });
    });
    await page.getByRole("button", { name: "更新内容", exact: true }).click();
    await page.getByText("抖音视频下载验证。", { exact: true }).click();
    await page.getByRole("dialog", { name: "作品详情" }).waitFor();
    assert.equal(
      await page.getByRole("link", { name: "查看原作品" }).getAttribute("href"),
      "https://www.douyin.com/video/1900000000000000300",
    );
    const videoDownload = page.waitForEvent("download");
    await page.getByRole("button", { name: "下载视频 1", exact: true }).click();
    assert.equal((await videoDownload).suggestedFilename(), "video.mp4");
    await page.keyboard.press("Escape");
    await page.getByRole("dialog").waitFor({ state: "hidden" });
    await page.getByText("抖音图文下载验证。", { exact: true }).click();
    await page.getByRole("dialog", { name: "作品详情" }).waitFor();
    assert.equal(
      await page.getByRole("link", { name: "查看原作品" }).getAttribute("href"),
      "https://www.douyin.com/note/1900000000000000301",
    );
    for (const index of [1, 2]) {
      const imageDownload = page.waitForEvent("download");
      await page
        .getByRole("button", { name: `下载图片 ${index}`, exact: true })
        .click();
      assert.equal(
        (await imageDownload).suggestedFilename(),
        `douyin-photo-${index}.webp`,
      );
    }
    assert.deepEqual(douyinAssets, [
      "video",
      "douyin-photo-1",
      "douyin-photo-2",
    ]);
    await page.screenshot({
      path: path.join(output, "douyin-gallery-detail.png"),
      fullPage: true,
    });
    await page.setViewportSize({ width: 320, height: 1000 });
    await page.evaluate(
      () =>
        new Promise((resolve) =>
          requestAnimationFrame(() => requestAnimationFrame(resolve)),
        ),
    );
    assert.ok(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth + 1,
      ),
      "Douyin detail overflow at 320",
    );
    await page.screenshot({
      path: path.join(output, "douyin-gallery-mobile.png"),
      fullPage: true,
    });
    await page.keyboard.press("Escape");
    await page.getByRole("dialog").waitFor({ state: "hidden" });
    assert.ok(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth + 1,
      ),
      "Douyin feed overflow at 320",
    );
    await page.screenshot({
      path: path.join(output, "douyin-feed-mobile.png"),
      fullPage: true,
    });
    await page.setViewportSize({ width: 1440, height: 1000 });
    await page.getByRole("button", { name: "个人设置", exact: true }).click();
    for (const width of [1280, 768, 390, 320]) {
      await page.setViewportSize({ width, height: 1000 });
      await page.evaluate(
        () =>
          new Promise((resolve) =>
            requestAnimationFrame(() => requestAnimationFrame(resolve)),
          ),
      );
      const offenders = await page.evaluate(() =>
        Array.from(document.querySelectorAll("body *"))
          .map((element) => ({
            tag: element.tagName,
            cls: element.className?.toString(),
            rect: element.getBoundingClientRect(),
          }))
          .filter(
            (row) => row.rect.width > 0 && row.rect.right > innerWidth + 1,
          )
          .map((row) => ({
            tag: row.tag,
            cls: row.cls,
            right: row.rect.right,
            width: row.rect.width,
          }))
          .slice(0, 15),
      );
      if (offenders.length) {
        console.log("Layout diagnostics", width, JSON.stringify(offenders));
        console.log(
          await page.locator(".topbar").evaluate((element) =>
            [element, ...element.querySelectorAll("*")].map((node) => ({
              tag: node.tagName,
              cls: node.className?.toString(),
              width: node.getBoundingClientRect().width,
              left: node.getBoundingClientRect().left,
              display: getComputedStyle(node).display,
              shrink: getComputedStyle(node).flexShrink,
              min: getComputedStyle(node).minWidth,
            })),
          ),
        );
      }
      assert.ok(
        await page.evaluate(
          () => document.documentElement.scrollWidth <= window.innerWidth + 1,
        ),
        "Overflow at " + width,
      );
    }
    await page.screenshot({
      path: path.join(output, "settings-mobile.png"),
      fullPage: true,
    });
    await page.setViewportSize({ width: 1440, height: 1000 });
    await page.getByRole("button", { name: "EN", exact: true }).click();
    await page
      .getByRole("heading", { name: "Settings", exact: true })
      .waitFor();
    await page.getByRole("button", { name: "中文", exact: true }).click();
    await page.getByRole("button", { name: "退出登录" }).click();
    await page.getByRole("button", { name: "登录", exact: true }).waitFor();
    assert.deepEqual(errors, []);
    console.log(
      "Browser flow passed: authentication, Key persistence, TikTok regression, Twitter text/quote/mixed/animation, Douyin share-message author confirmation and video/gallery downloads, platform filters, stable asset IDs, HLS state, locale, mobile layout and logout. TikHub responses simulated; no paid calls.",
    );
  } finally {
    await browser.close();
  }
})().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
