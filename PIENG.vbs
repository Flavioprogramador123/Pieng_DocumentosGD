Set WshShell = CreateObject("WScript.Shell")
WshShell.Run chr(34) & "C:\Users\flavi\projeto\Automacao_Equatorial01\INICIAR_SISTEMA.bat" & Chr(34), 0
Set WshShell = Nothing

' Para adicionar ícone ao atalho VBS:
' 1. Clique com botão direito no atalho VBS
' 2. Propriedades > Alterar ícone
' 3. Procurar: C:\Users\flavi\projeto\Automacao_Equatorial01\backend\logo\pieng-icon.ico
