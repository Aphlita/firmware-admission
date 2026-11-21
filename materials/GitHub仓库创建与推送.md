# GitHub 仓库创建与推送

## 0. 2026-11-21 连通性复测

| 测试 | 结果 |
|---|---|
| DNS `github.com` | 解析到 `20.205.243.166` |
| TCP `github.com:443` | 通 |
| `curl --noproxy '*' https://github.com` | **200 OK** |
| `git ls-remote https://github.com/git/git.git` | 能拿到 refs（GitHub 直连可用） |
| `https://api.github.com/` | **200** |
| `https://raw.githubusercontent.com/...` | 超时（不影响 `git push`） |
| 当前环境代理 `127.0.0.1:7892` | 对本机 git/curl 不稳定，需绕过 |
| `git ls-remote https://github.com/langqwu/firmware-admission.git` | `Repository not found`（仓库还不存在） |

结论：**GitHub 直连是通的**，之前失败主要是环境代理 `127.0.0.1:7892` 不稳定。
在 PowerShell 里先清掉代理变量，再执行 git：

```powershell
$env:HTTP_PROXY=''
$env:HTTPS_PROXY=''
$env:ALL_PROXY=''
$env:NO_PROXY='github.com,api.github.com'
```

当前仍然缺的是 **GitHub 登录/授权**：本机没有 `gh`，也没有 `GH_TOKEN`/`GITHUB_TOKEN`，
所以我不能代替你创建远程仓库或 push；需要你在能登录 GitHub 的浏览器/凭据环境里完成一次。

---

> 当前状态（2026-11-21）：
> - 本地 `firmware-admission` 已有完整 git 历史，但 **`git remote -v` 为空**，没有 GitHub 远程仓库；
> - 本机 **没有安装 `gh`**，也没有设置 `GH_TOKEN` / `GITHUB_TOKEN`；
> - 直接访问 `github.com:443` 已复测可用，但默认代理（`127.0.0.1:7892`）不稳定，需要 bypass。
> 因此仓库需要你在能访问 GitHub 的机器/浏览器上创建一次，然后 `git push`。

---

## 方式一：网页创建 + git push（最稳，推荐）

### 1. 在 GitHub 网页创建空仓库

1. 打开 <https://github.com/new>；
2. Repository name：`firmware-admission`；
3. 选择 **Private**（固件/竞赛材料，不建议公开）；
4. **不要**勾选 “Add a README file / .gitignore / license”（本地已有历史，勾了会增加一次合并）；
5. 点 Create repository。

### 2. 在本地项目目录配置 remote

把 `<你的GitHub用户名>` 换成实际用户名：

```powershell
cd E:\dsh_talking\firmware-admission
git branch -M main
git remote add origin https://github.com/<你的GitHub用户名>/firmware-admission.git
git remote -v
```

应看到：

```text
origin  https://github.com/<你的GitHub用户名>/firmware-admission.git (fetch)
origin  https://github.com/<你的GitHub用户名>/firmware-admission.git (push)
```

### 3. 推送

```powershell
git push -u origin main
```

如果弹出 GitHub 登录：

- 推荐用浏览器登录 / Personal Access Token；
- 不要用密码（GitHub 已不支持密码 push）；
- token 只填在凭据提示里，不要写进仓库文件。

如果网页建仓库时勾了 README，先合并再推：

```powershell
git pull --rebase origin main
git push -u origin main
```

### 4. 验证

```powershell
git log --oneline -3
git ls-remote origin
```

能看到提交哈希和 `refs/heads/main` 即可。

---

## 方式二：GitHub CLI（装了 gh 且已登录）

```powershell
winget install --id GitHub.cli -e
gh auth login
cd E:\dsh_talking\firmware-admission
gh repo create firmware-admission --private --source=. --remote=origin --push
```

`gh auth login` 会要求浏览器/设备码登录；这一步必须由你完成，我无法代填账号密码。

---

## 推送前检查（重要）

```powershell
git status --short
git check-ignore -v data/firmware
git ls-files | Select-String -Pattern 'data/|sources/|\.env|token|secret'
```

要求：

- `data/`、`sources/`、`*.bin`、`*.zip` 不被跟踪；
- 没有任何 token/密钥被 git 跟踪；
- 未跟踪的 `docs/03`、`docs/04`、`.arts/` 是否要推，由你决定；它们目前不在提交里，不会被 push。

## 队友 clone

仓库建好后发给王同学/苏同学：

```powershell
git clone https://github.com/<你的GitHub用户名>/firmware-admission.git
cd firmware-admission
python -m pytest -q
```

标注任务从 `materials/标注任务分配-王同学-苏同学.md` 开始。

## 如果 GitHub 一直连不上

当前环境访问 GitHub 被代理拦截。可以：

1. 换一台能直连 GitHub 的电脑执行上面的 push；
2. 或先把本地仓库打成 bundle 交给能推送的人：

```powershell
git bundle create firmware-admission.bundle --all
```

对方：

```powershell
git clone firmware-admission.bundle firmware-admission
cd firmware-admission
git remote set-url origin https://github.com/<用户名>/firmware-admission.git
git push -u origin main
```

不要为了绕过网络把仓库公开或上传到不明网盘；竞赛材料优先私有仓库。
