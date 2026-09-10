Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName)
WshShell.Run Chr(34) & WshShell.CurrentDirectory & "\INICIAR_SISTEMA.bat" & Chr(34), 0
Set WshShell = Nothing

' Para adicionar ícone ao atalho VBS:
' 1. Clique com botão direito no atalho VBS
' 2. Propriedades > Alterar ícone
' 3. Procurar: backend\logo\pieng-icon.ico
