const STORAGE_KEY = 'equatorial_device_id'

/** ID persistente do navegador — usado para reconhecer máquinas já autorizadas. */
export function getDeviceId() {
  try {
    let id = localStorage.getItem(STORAGE_KEY)
    if (!id) {
      id = crypto.randomUUID()
      localStorage.setItem(STORAGE_KEY, id)
    }
    return id
  } catch {
    return 'anonymous-device'
  }
}
