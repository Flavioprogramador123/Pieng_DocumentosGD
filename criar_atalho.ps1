$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut([Environment]::GetFolderPath('Desktop') + '\PIENG - Automacao Equatorial.lnk')
$Shortcut.TargetPath = 'C:\Users\flavi\projeto\Automacao_Equatorial01\PIENG.vbs'
$Shortcut.WorkingDirectory = 'C:\Users\flavi\projeto\Automacao_Equatorial01'
$Shortcut.Description = 'PIENG - Sistema de Automacao Equatorial'
$Shortcut.Save()
Write-Host 'Atalho criado com sucesso na area de trabalho!'
