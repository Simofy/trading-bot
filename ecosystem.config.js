module.exports = {
  apps: [{
    name: 'trading-bot',
    script: 'main.py',
    interpreter: 'python3',
    cwd: '/root/projects/trading-bot',
    instances: 1,
    autorestart: true,
    watch: false,
    max_memory_restart: '1G',
    env: {
      NODE_ENV: 'production',
      PYTHONPATH: '/root/projects/trading-bot'
    },
    error_file: './logs/pm2-error.log',
    out_file: './logs/pm2-out.log',
    log_file: './logs/pm2-combined.log',
    time: true,
    restart_delay: 5000,
    max_restarts: 10,
    min_uptime: '30s'
  }, {
    name: 'trading-dashboard',
    script: 'dashboard_standalone.py',
    interpreter: 'python3',
    cwd: '/root/projects/trading-bot',
    instances: 1,
    autorestart: true,
    watch: false,
    max_memory_restart: '512M',
    env: {
      NODE_ENV: 'production',
      PYTHONPATH: '/root/projects/trading-bot',
      DASHBOARD_HOST: '0.0.0.0',
      DASHBOARD_PORT: '8000'
    },
    error_file: './logs/dashboard-error.log',
    out_file: './logs/dashboard-out.log',
    log_file: './logs/dashboard-combined.log',
    time: true,
    restart_delay: 3000,
    max_restarts: 10,
    min_uptime: '20s'
  }]
}; 