# Как отправить Agent Enhancer на проверку Anthropic

**Read when:** ты отправляешь готовый Agent Enhancer Utilities в Claude Connectors
Directory.

**Skip when:** нужно тестировать или исправлять коннектор.

**Related:** [Claude landing page](https://liberated.site/claude) и
[Privacy policy](https://liberated.site/privacy).

## 1. Открой форму

Войди в нужную Claude-организацию и открой:

**[Submit a new connector](https://claude.ai/admin-settings/directory/submissions/new)**

Если форма недоступна или открылась read-only, пришли нам screenshot.

## 2. Подключи сервер

В поле MCP server URL вставь:

```text
https://liberated.site/mcp/claude
```

Если портал спрашивает дополнительные параметры, выбери:

```text
Type: Remote MCP server
Transport: Streamable HTTP
URL: Same URL for all users
Authentication: No authentication
```

Портал должен найти:

```text
37 tools
```

Если количество другое или видны warnings, пришли нам screenshot.

## 3. Заполни Listing

<details>
<summary><strong>Открыть готовые тексты для Listing</strong></summary>

**Name**

```text
Agent Enhancer Utilities
```

**Tagline**

```text
Reliability tools for safer agent workflows
```

**Description**

```text
Agent Enhancer Utilities provides deterministic, bounded tools for coordinating parallel agents, planning and recovering retry-sensitive workflows, testing HTTP failure paths, and reviewing MCP and x402 contracts. The connector exposes 37 action-specific tools across 24 free modules. It uses no authentication, cannot transfer money or cryptocurrency, does not access Claude conversations or memory, and does not require an Agent Enhancer account or API key. Use opaque or synthetic identifiers only; do not submit credentials, personal data, customer content, wallet secrets, or conversation history.
```

**Permanent slug**

```text
agent-enhancer-utilities
```

Если этот slug занят, не придумывай новый — пришли нам screenshot.

**Links**

```text
Documentation: https://liberated.site/claude
Privacy policy: https://liberated.site/privacy
Support: https://liberated.site/support
Terms: https://liberated.site/terms
```

**Icon**

**[Скачать готовую PNG-иконку](https://liberated.site/icon.png)**

Если нужны categories, выбери от одной до трёх из доступных вариантов:

```text
Developer Tools
Productivity
Utilities или Data — только если такой вариант есть
```

Не выбирай Finance, Payments, Crypto или AI media.

</details>

## 4. Заполни Use cases

<details>
<summary><strong>Открыть готовые тексты для Use cases</strong></summary>

**Primary use cases**

```text
Use Agent Enhancer Utilities when an agent workflow can repeat, run in parallel, time out, hit a quota, go stale, or create duplicates. It can coordinate ownership and capacity, plan safe recovery, maintain opaque workflow checkpoints, generate bounded HTTP failure fixtures, and inspect MCP or x402 contracts. It should not be used for ordinary one-time low-risk tasks, messaging, content retrieval, payments, wallet actions, or any task requiring access to Claude memory or conversation history.
```

**Prerequisites**

```text
No Agent Enhancer account, API key, OAuth flow, paid plan, or separate setup is required. Users only connect the public no-auth remote MCP server.
```

**Read or write**

Выбери:

```text
Both read and write
```

Если нужно пояснение, вставь:

```text
Read-only tools inspect caller-supplied contracts or query bounded status. Write tools create or update short-lived Agent Enhancer coordination and test records. They do not send messages, modify third-party accounts, or transfer money or cryptocurrency.
```

</details>

## 5. Заполни Company и Authentication

<details>
<summary><strong>Открыть Company и Authentication</strong></summary>

**Company**

```text
Company or publisher: 2740993 ALBERTA INC.
Website: https://liberated.site
Support email: hello@artiehinz.com
```

**Authentication**

Выбери:

```text
No authentication
```

Если портал просит test account или credentials, вставь:

```text
This is an authless public MCP server. No account, API key, OAuth flow, or test credentials are required. Reviewers can connect directly to the HTTPS Streamable HTTP endpoint. Every public tool is free.
```

Если портал всё равно требует login или password, пришли нам screenshot.

</details>

## 6. Ответь на Data handling

<details>
<summary><strong>Открыть готовые ответы для Data handling</strong></summary>

Выбери:

```text
Underlying API: First-party / our own service
Personal health data: No
Sponsored content or advertising: No
Access to Claude memory, chats, or files: No
Payments or cryptocurrency execution: No
```

Если нужно текстовое пояснение, вставь:

```text
The connector calls the first-party Agent Enhancer Utilities service hosted at liberated.site. It does not proxy an unaffiliated third-party API. It accepts only bounded tool fields selected by the user and does not request Claude memory, chat history, conversation summaries, or user files. Raw tool inputs and outputs are not retained in analytics. Short-lived coordination or replay records store opaque derived keys and bounded values according to each tool's published retention contract. Cloudflare and DigitalOcean process limited infrastructure metadata as described in the privacy policy. The connector does not handle personal health data or sponsored content.
```

Allowed link URIs оставь пустым: коннектор не открывает внешние ссылки.
Carousel screenshots не нужны: это MCP connector без MCP App UI.

</details>

## 7. Заполни Test & launch

<details>
<summary><strong>Открыть готовые ответы для Test & launch</strong></summary>

**Reviewer instructions**

```text
No test account or credentials are required. Connect to https://liberated.site/mcp/claude using Streamable HTTP and No authentication. Confirm that 37 action-specific tools sync successfully. Use synthetic or opaque values only. The connector is free and cannot transfer money or cryptocurrency. Documentation and safety boundaries are available at https://liberated.site/claude.
```

**Availability**

```text
Available now (public beta)
```

Если обязательно нужна дата, укажи:

```text
2026-07-25
```

В вопросе о testing всех tools выбери **Yes**.

В Compliance подтверди следующие факты:

- connector использует наш first-party service;
- он не переводит деньги или cryptocurrency;
- он не создаёт AI images, video или audio;
- он не собирает Claude conversations, memory или files;
- публичные documentation и privacy доступны.

Если формулировка в портале означает что-то другое, пришли нам screenshot.

</details>

## 8. Отправь на review

На финальном экране проверь:

```text
Name: Agent Enhancer Utilities
MCP URL: https://liberated.site/mcp/claude
Authentication: No authentication
Slug: agent-enhancer-utilities
```

Нажми **Submit** один раз.

После отправки пришли нам:

- screenshot финального статуса;
- submission URL или ID;
- permanent slug;
- название submitting organization;
- все последующие письма или вопросы от Anthropic.
