import { networkInterfaces } from 'node:os'
import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

type BackendVersionResponse = {
  service?: string
  success?: boolean
}

const CLARION_SERVICE_NAME = 'law-firm-feedback-saas'

const normalizeTarget = (target: string): string => target.replace(/\/+$/, '')

const localProxyCandidates = (): string[] => {
  const candidates = ['http://127.0.0.1:5000', 'http://localhost:5000']
  const seen = new Set(candidates.map((target) => normalizeTarget(target)))

  for (const addresses of Object.values(networkInterfaces())) {
    for (const address of addresses || []) {
      if (address.family !== 'IPv4' || address.internal) continue
      const target = `http://${address.address}:5000`
      const normalized = normalizeTarget(target)
      if (seen.has(normalized)) continue
      seen.add(normalized)
      candidates.push(target)
    }
  }

  return candidates
}

const isClarionBackend = async (target: string): Promise<boolean> => {
  try {
    const response = await fetch(`${normalizeTarget(target)}/api/version`)
    if (!response.ok) return false
    const payload = (await response.json()) as BackendVersionResponse
    return payload.success === true && payload.service === CLARION_SERVICE_NAME
  } catch {
    return false
  }
}

const resolveApiProxyTarget = async (env: Record<string, string>): Promise<string> => {
  const explicitTarget = env.VITE_API_PROXY_TARGET || env.CLARION_API_PROXY_TARGET
  if (explicitTarget) {
    return explicitTarget
  }

  for (const candidate of localProxyCandidates()) {
    if (await isClarionBackend(candidate)) {
      return candidate
    }
  }

  return 'http://127.0.0.1:5000'
}

export default defineConfig(async ({ mode }) => {
  const env = loadEnv(mode, __dirname, '')
  const apiProxyTarget = await resolveApiProxyTarget(env)

  return {
    plugins: [react()],
    resolve: {
      alias: {
        '@': path.resolve(__dirname, './src'),
      },
    },
    server: {
      host: '0.0.0.0',
      port: 8081,
      allowedHosts: true,
      proxy: {
        '/api': {
          target: apiProxyTarget,
          changeOrigin: true,
          secure: false,
        },
      },
    },
  }
})
