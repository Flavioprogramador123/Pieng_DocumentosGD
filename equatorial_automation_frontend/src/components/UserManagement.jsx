import { useEffect, useState } from 'react'
import { Button } from '@/components/ui/button.jsx'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card.jsx'
import { Input } from '@/components/ui/input.jsx'
import { Label } from '@/components/ui/label.jsx'
import { Alert, AlertDescription } from '@/components/ui/alert.jsx'
import { Trash2, UserPlus, KeyRound } from 'lucide-react'
import { apiJson } from '@/utils/api.js'

export function UserManagement() {
  const [users, setUsers] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [newUser, setNewUser] = useState({ username: '', password: '' })
  const [resetPass, setResetPass] = useState({ username: '', password: '' })

  const loadUsers = async () => {
    setLoading(true)
    setError('')
    try {
      const { response, data } = await apiJson('/auth/users')
      if (response.ok && data.success) {
        setUsers(data.users || [])
      } else {
        setError(data.error || 'Erro ao listar usuários.')
      }
    } catch {
      setError('Falha ao conectar ao servidor.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadUsers()
  }, [])

  const handleCreate = async (e) => {
    e.preventDefault()
    setError('')
    const { response, data } = await apiJson('/auth/users', {
      method: 'POST',
      body: JSON.stringify(newUser),
    })
    if (response.ok && data.success) {
      setNewUser({ username: '', password: '' })
      await loadUsers()
      return
    }
    setError(data.error || 'Erro ao criar usuário.')
  }

  const handleDelete = async (username) => {
    if (!window.confirm(`Excluir usuário "${username}"?`)) return
    const { response, data } = await apiJson(`/auth/users/${encodeURIComponent(username)}`, {
      method: 'DELETE',
    })
    if (response.ok && data.success) {
      await loadUsers()
      return
    }
    setError(data.error || 'Erro ao excluir.')
  }

  const handleToggleActive = async (username, active) => {
    const { response, data } = await apiJson(`/auth/users/${encodeURIComponent(username)}/active`, {
      method: 'PUT',
      body: JSON.stringify({ active: !active }),
    })
    if (response.ok && data.success) {
      await loadUsers()
      return
    }
    setError(data.error || 'Erro ao alterar status.')
  }

  const handleResetPassword = async (e) => {
    e.preventDefault()
    if (!resetPass.username || !resetPass.password) return
    setError('')
    const { response, data } = await apiJson(
      `/auth/users/${encodeURIComponent(resetPass.username)}/password`,
      {
        method: 'PUT',
        body: JSON.stringify({ password: resetPass.password }),
      },
    )
    if (response.ok && data.success) {
      setResetPass({ username: '', password: '' })
      alert('Senha alterada com sucesso.')
      return
    }
    setError(data.error || 'Erro ao redefinir senha.')
  }

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Usuários de segundo nível</CardTitle>
          <CardDescription>
            Somente o master pode criar, desativar ou excluir contas operacionais.
            A senha master fica apenas no <code className="text-xs">.env</code> do servidor.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {error && (
            <Alert variant="destructive" className="mb-4">
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          <form onSubmit={handleCreate} className="grid gap-4 md:grid-cols-3 items-end mb-6 p-4 border rounded-lg bg-slate-50">
            <div className="space-y-2">
              <Label>Novo usuário</Label>
              <Input
                value={newUser.username}
                onChange={(e) => setNewUser((p) => ({ ...p, username: e.target.value }))}
                placeholder="operador1"
                autoComplete="off"
              />
            </div>
            <div className="space-y-2">
              <Label>Senha inicial</Label>
              <Input
                type="password"
                value={newUser.password}
                onChange={(e) => setNewUser((p) => ({ ...p, password: e.target.value }))}
                autoComplete="new-password"
              />
            </div>
            <Button type="submit">
              <UserPlus className="mr-2 h-4 w-4" />
              Criar usuário
            </Button>
          </form>

          {loading ? (
            <p className="text-sm text-muted-foreground">Carregando...</p>
          ) : users.length === 0 ? (
            <p className="text-sm text-muted-foreground">Nenhum usuário secundário cadastrado.</p>
          ) : (
            <div className="space-y-2">
              {users.map((u) => (
                <div
                  key={u.username}
                  className="flex flex-wrap items-center justify-between gap-2 p-3 border rounded-lg"
                >
                  <div>
                    <p className="font-medium">{u.username}</p>
                    <p className="text-xs text-muted-foreground">
                      {u.active ? 'Ativo' : 'Desativado'}
                      {u.created_at ? ` · criado ${u.created_at.slice(0, 10)}` : ''}
                    </p>
                  </div>
                  <div className="flex gap-2">
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => handleToggleActive(u.username, u.active)}
                    >
                      {u.active ? 'Desativar' : 'Ativar'}
                    </Button>
                    <Button
                      size="sm"
                      variant="destructive"
                      onClick={() => handleDelete(u.username)}
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <KeyRound className="h-5 w-5" />
            Redefinir senha
          </CardTitle>
          <CardDescription>Altere a senha de um usuário secundário.</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleResetPassword} className="grid gap-4 md:grid-cols-3 items-end">
            <div className="space-y-2">
              <Label>Usuário</Label>
              <Input
                value={resetPass.username}
                onChange={(e) => setResetPass((p) => ({ ...p, username: e.target.value }))}
                placeholder="operador1"
              />
            </div>
            <div className="space-y-2">
              <Label>Nova senha</Label>
              <Input
                type="password"
                value={resetPass.password}
                onChange={(e) => setResetPass((p) => ({ ...p, password: e.target.value }))}
              />
            </div>
            <Button type="submit" variant="secondary">Salvar nova senha</Button>
          </form>
        </CardContent>
      </Card>
    </div>
  )
}
