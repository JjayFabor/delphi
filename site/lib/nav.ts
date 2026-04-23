export interface NavItem {
  title: string
  slug: string
}

export interface NavSection {
  title: string
  items: NavItem[]
}

export const docsNav: NavSection[] = [
  {
    title: 'Getting Started',
    items: [
      { title: 'Introduction',  slug: 'introduction' },
      { title: 'Prerequisites', slug: 'prerequisites' },
      { title: 'Quick Start',   slug: 'quick-start' },
      { title: 'Configuration', slug: 'configuration' },
    ],
  },
  {
    title: 'Core Concepts',
    items: [
      { title: 'Memory',      slug: 'memory' },
      { title: 'Skills',      slug: 'skills' },
      { title: 'Connectors',  slug: 'connectors' },
      { title: 'Sub-agents',  slug: 'sub-agents' },
      { title: 'Scheduler',   slug: 'scheduler' },
    ],
  },
  {
    title: 'Guides',
    items: [
      { title: 'Connecting Telegram',  slug: 'guides/connecting-telegram' },
      { title: 'Connecting Discord',   slug: 'guides/connecting-discord' },
      { title: 'Adding a Connector',   slug: 'guides/adding-a-connector' },
      { title: 'Writing a Skill',      slug: 'guides/writing-a-skill' },
      { title: 'WSL2 Setup',           slug: 'guides/wsl2-setup' },
      { title: 'Linux Setup',          slug: 'guides/linux-setup' },
      { title: 'macOS Setup',          slug: 'guides/macos-setup' },
      { title: 'Docker Setup',         slug: 'guides/docker-setup' },
    ],
  },
]

export const apiNav: NavSection[] = [
  {
    title: 'API Reference',
    items: [
      { title: 'Overview', slug: 'overview' },
    ],
  },
  {
    title: 'Tools',
    items: [
      { title: 'Bash',              slug: 'bash' },
      { title: 'Read / Write / Edit', slug: 'read-write-edit' },
      { title: 'Glob / Grep',       slug: 'glob-grep' },
    ],
  },
  {
    title: 'Scheduler Tools',
    items: [
      { title: 'scheduler_add',    slug: 'scheduler-add' },
      { title: 'scheduler_list',   slug: 'scheduler-list' },
      { title: 'scheduler_remove', slug: 'scheduler-remove' },
      { title: 'schedule_once',    slug: 'schedule-once' },
    ],
  },
  {
    title: 'Sub-agent Tools',
    items: [
      { title: 'subagent_list',   slug: 'subagent-list' },
      { title: 'subagent_create', slug: 'subagent-create' },
      { title: 'subagent_run',    slug: 'subagent-run' },
    ],
  },
  {
    title: 'Connector Tools',
    items: [
      { title: 'connector_info', slug: 'connector-info' },
      { title: 'connector_add',  slug: 'connector-add' },
    ],
  },
  {
    title: 'Shared Context',
    items: [
      { title: 'share',           slug: 'share' },
      { title: 'revoke',          slug: 'revoke' },
      { title: 'shared (pull)',   slug: 'shared-pull' },
    ],
  },
  {
    title: 'Learning Tools',
    items: [
      { title: 'learn',                              slug: 'learn' },
      { title: 'skill_list / read / write / delete', slug: 'skill-tools' },
    ],
  },
]
