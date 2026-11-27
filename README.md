# 可转债跟踪工作台 · 云端部署包

部署后你将得到：
- 一个**固定链接**（GitHub Pages，免费），手机/电脑随时打开就是工作台
- **每个交易日北京时间约 08:30** 自动更新：13 只转债最新价/涨跌幅/溢价率 + 近 14 天公告（赎回/下修/回售/评级/兑付）
- 电脑关机也照常更新（更新在 GitHub 云端运行）

## 文件清单
| 文件 | 作用 |
|---|---|
| index.html | 工作台页面（打开自动读 data.json） |
| fetch.py | 每日抓取脚本（东方财富行情+公告接口） |
| data.json | 数据文件（每天被自动覆盖，初始为 11-27 种子数据） |
| .github/workflows/daily-update.yml | 定时任务：每交易日 08:30 运行 fetch.py 并提交 |
| .nojekyll | GitHub Pages 必需 |

## 部署步骤（约 10 分钟，只需做一次）
1. **注册 GitHub**：https://github.com 注册账号（免费）
2. **新建仓库**：右上角 + → New repository → 名字填 `cb-workbench` → 选 **Public** → Create
   - ⚠️ 必须 Public（免费账户的 Pages 只能公开）。页面不含任何个人信息，公开无隐私风险
3. **上传文件**：仓库页面 → Add file → Upload files → 把本包**解压后的所有文件**拖进去
   - ⚠️ 关键：`.github` 这个文件夹要连同里面的 `workflows/daily-update.yml` 一起拖进去（直接拖整个解压出来的文件夹即可保留结构）→ Commit changes
4. **开启固定链接**：仓库 Settings → 左侧 Pages → Source 选 `Deploy from a branch`，分支选 `main` + `/ (root)` → Save → 等 1-2 分钟
   - 你的链接：**https://你的用户名.github.io/cb-workbench/**
5. **验证定时任务**：仓库上方 Actions 标签 → 左侧 Daily-update workflow → 右侧 **Run workflow** → 绿点运行 → 等 1 分钟，`Run workflow` 变绿勾即成功；刷新你的链接，顶栏应显示"云端数据 + 刚才的时间"
   - 首次运行 Actions 若提示需要批准（"I understand my workflows, go ahead and run them"），点一下批准即可

## 日常使用
- 书签保存你的 Pages 链接，每个交易日 08:30 后打开即是最新数据
- 想临时刷新：页面右上角 ⟳ 刷新行情（只刷价格）；或去 Actions 手动 Run workflow（价格+公告全刷）
- 修改跟踪名单：编辑仓库里的 fetch.py 顶部 BONDS 列表（一行一只转债）和 index.html 里的 CB 数组，提交后自动生效——或者回聊天里让助手帮你改

## 说明与边界
- 公告来源：东方财富公告接口按关键词筛查，可能漏掉个别措辞特殊的公告；重大决策请以上交所/深交所/巨潮资讯网原文为准
- GitHub 定时任务可能有几分钟到十几分钟延迟；周末与节假日不运行（cron 限周一到五）
- 免费额度：public 仓库 Actions 不限量（3000 分钟/月的软限制对本任务绰绰有余）
- 溢价率来自东方财富可转债表，若当日接口异常会自动保留上一次的值（不会清空）
