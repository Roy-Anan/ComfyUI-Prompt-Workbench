# 把项目文档上传到 GitHub（不需要命令行）

目标仓库：

https://github.com/Roy-Anan/ComfyUI-Prompt-Workbench

这个 ZIP 解压后会得到 `ComfyUI-Prompt-Workbench-Docs` 文件夹，里面包含
README、docs 文件夹和本说明。

## 第一步：下载并解压

1.  下载本压缩包。
2.  在 Windows 文件资源管理器中找到 ZIP 文件。
3.  右键 ZIP → "全部解压缩"。
4.  打开解压后的 `ComfyUI-Prompt-Workbench-Docs` 文件夹。

## 第二步：打开仓库上传页面

1.  打开 https://github.com/Roy-Anan/ComfyUI-Prompt-Workbench
2.  登录你的 GitHub 账号。
3.  点击仓库页面的 **Add file**。
4.  选择 **Upload files**。

## 第三步：上传文件

1.  在文件资源管理器中打开刚才解压的文件夹。
2.  选中里面的 `README.md`、`UPLOAD_GUIDE.md` 和 `docs` 文件夹。
3.  将它们拖到 GitHub 网页的上传区域。
4.  等待上传完成，检查页面显示的文件路径是否正确：`docs/` 和
    `docs/decisions/` 应保留目录层级。

如果网页不接受整个文件夹拖放，可以先进入 `docs`
文件夹，按目录分批上传；先上传根目录文件，再上传 docs 中的文件，最后上传
`docs/decisions` 中的 ADR 文件。

## 第四步：保存上传

1.  页面下方找到 **Commit changes**。
2.  提交说明可以填写：`docs: add project baseline and handoff documentation`
3.  选择直接提交到 `main` 分支（默认选项）。
4.  点击 **Commit changes**。

这次上传只增加项目文档，不会覆盖现有代码（仓库目前检查时为空）。

## 第五步：告诉我完成

上传后回到 ChatGPT，告诉我"上传好了"。我会再检查仓库里的 README 和 docs
文件，确认目录和内容齐全，再继续工程骨架。

## 隐私提醒

-   不要把 GitHub 密码、Personal Access Token 或任何密钥发给我。
-   不要上传 ComfyUI 模型、LoRA 权重、生成图片或私人配置文件。
-   这次只上传本压缩包中的 Markdown 文档。
