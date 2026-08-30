import { useEffect, useState } from 'react'
import { Button } from '@/components/ui/button.jsx'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card.jsx'
import { Input } from '@/components/ui/input.jsx'
import { Label } from '@/components/ui/label.jsx'
import { Alert, AlertDescription } from '@/components/ui/alert.jsx'
import { apiJson } from '@/utils/api.js'
import { getDeviceId } from '@/utils/deviceId.js'

export function Login({ onSuccess, authStatus, confirmToken = null }) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [verifyStep, setVerifyStep] = useState(false)
  const [verifyEmail, setVerifyEmail] = useState('')
  const [verifyCode, setVerifyCode] = useState('')
  const [pendingToken, setPendingToken] = useState(confirmToken || '')
  const [emailMasked, setEmailMasked] = useState('')
  const [codeSent, setCodeSent] = useState(false)
  const [devCode, setDevCode] = useState('')
  const [sendingCode, setSendingCode] = useState(false)

  useEffect(() => {
    if (confirmToken) {
      setPendingToken(confirmToken)
      setVerifyStep(true)
    }
  }, [confirmToken])

  const submitConfirm = async (token, code) => {
    setError('')
    setLoading(true)
    try {
      const { response, data } = await apiJson('/auth/confirm-device', {
        method: 'POST',
        body: JSON.stringify({
          token,
          device_id: getDeviceId(),
          code: code || undefined,
        }),
      })
      if (response.ok && data.success) {
        onSuccess(data.user)
        return
      }
      setError(data.error || 'Não foi possível confirmar o dispositivo.')
    } catch {
      setError('Não foi possível conectar ao servidor.')
    } finally {
      setLoading(false)
    }
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const { response, data } = await apiJson('/auth/login', {
        method: 'POST',
        body: JSON.stringify({
          username,
          password,
          device_id: getDeviceId(),
        }),
      })
      if (response.ok && data.success) {
        if (data.verification_required) {
          setPendingToken(data.verification_token || '')
          setEmailMasked(data.email_masked || authStatus?.verify_email_masked || '')
          setVerifyStep(true)
          setCodeSent(false)
          setVerifyCode('')
          setVerifyEmail('')
          setLoading(false)
          return
        }
        onSuccess(data.user)
        return
      }
      setError(data.error || 'Falha no login.')
    } catch {
      setError('Não foi possível conectar ao servidor.')
    } finally {
      setLoading(false)
    }
  }

  const handleSendCode = async (e) => {
    e.preventDefault()
    if (!pendingToken) {
      setError('Faça login novamente.')
      return
    }
    if (!verifyEmail.trim()) {
      setError('Informe o e-mail cadastrado.')
      return
    }

    setError('')
    setSendingCode(true)
    try {
      const { response, data } = await apiJson('/auth/send-device-code', {
        method: 'POST',
        body: JSON.stringify({
          verification_token: pendingToken,
          email: verifyEmail.trim(),
          device_id: getDeviceId(),
        }),
      })
      if (response.ok && data.success) {
        setCodeSent(true)
        setEmailMasked(data.email_masked || emailMasked)
        if (data.dev_code) {
          setDevCode(data.dev_code)
          setVerifyCode(data.dev_code)
        }
        return
      }
      setError(data.error || 'Não foi possível enviar o código.')
    } catch {
      setError('Não foi possível conectar ao servidor.')
    } finally {
      setSendingCode(false)
    }
  }

  const handleConfirmCode = async (e) => {
    e.preventDefault()
    if (!pendingToken) {
      setError('Faça login novamente.')
      return
    }
    if (!codeSent) {
      setError('Envie o código para o e-mail antes de confirmar.')
      return
    }
    await submitConfirm(pendingToken, verifyCode)
  }

  useEffect(() => {
    if (!confirmToken) return
    submitConfirm(confirmToken, null)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [confirmToken])

  if (confirmToken && loading && !error) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-50 to-slate-100">
        <p className="text-gray-600">Confirmando dispositivo...</p>
      </div>
    )
  }

  if (verifyStep && !confirmToken) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 flex items-center justify-center p-4">
        <Card className="w-full max-w-md shadow-lg">
          <CardHeader className="text-center space-y-3">
            <CardTitle className="text-2xl">Confirme este computador</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <form onSubmit={handleSendCode} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="verify-email">E-mail cadastrado</Label>
                <Input
                  id="verify-email"
                  type="email"
                  autoComplete="email"
                  value={verifyEmail}
                  onChange={(e) => setVerifyEmail(e.target.value)}
                  placeholder={emailMasked || 'seu@email.com'}
                  required
                />
              </div>
              <Button
                type="submit"
                variant="outline"
                className="w-full"
                disabled={sendingCode || !verifyEmail.trim()}
              >
                {sendingCode ? 'Enviando...' : 'Enviar código'}
              </Button>
            </form>

            {codeSent && (
              <form onSubmit={handleConfirmCode} className="space-y-4 pt-2 border-t">
                {devCode ? (
                  <p className="text-sm text-amber-800 bg-amber-50 border border-amber-200 rounded p-2 text-center">
                    Modo local — código: <strong className="text-lg tracking-widest">{devCode}</strong>
                  </p>
                ) : (
                  <p className="text-sm text-gray-600 text-center">
                    Código enviado para <strong>{emailMasked}</strong>
                  </p>
                )}
                <div className="space-y-2">
                  <Label htmlFor="verify-code">Código de 6 dígitos</Label>
                  <Input
                    id="verify-code"
                    inputMode="numeric"
                    autoComplete="one-time-code"
                    maxLength={6}
                    value={verifyCode}
                    onChange={(e) => setVerifyCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
                    placeholder="000000"
                    required
                  />
                </div>
                <Button type="submit" className="w-full" disabled={loading || verifyCode.length !== 6}>
                  {loading ? 'Confirmando...' : 'Confirmar'}
                </Button>
              </form>
            )}

            {error && (
              <Alert variant="destructive">
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}

            <Button
              type="button"
              variant="ghost"
              className="w-full"
              onClick={() => {
                setVerifyStep(false)
                setVerifyEmail('')
                setVerifyCode('')
                setPendingToken('')
                setCodeSent(false)
                setDevCode('')
                setError('')
              }}
            >
              Voltar ao login
            </Button>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 flex items-center justify-center p-4">
      <Card className="w-full max-w-md shadow-lg">
        <CardHeader className="text-center space-y-3">
          <img
            src="/brand/logo-app-96.png"
            alt="PIENG"
            className="h-16 w-16 mx-auto object-contain"
            onError={(e) => { e.currentTarget.style.display = 'none' }}
          />
          <CardTitle className="text-2xl">Automação Equatorial</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="login-user">Usuário</Label>
              <Input
                id="login-user"
                autoComplete="username"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="pieng"
                required
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="login-pass">Senha</Label>
              <Input
                id="login-pass"
                type="password"
                autoComplete="current-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
            </div>

            {error && (
              <Alert variant="destructive">
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}

            <Button type="submit" className="w-full" disabled={loading || !authStatus?.master_configured}>
              {loading ? 'Entrando...' : 'Entrar'}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  )
}
