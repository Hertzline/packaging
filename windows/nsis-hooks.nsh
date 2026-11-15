; Hertzline NSIS installer hooks (HZ-049 / AC-7.3).
; Wired via tauri.windows.bundle.json -> bundle.windows.nsis.installerHooks
; Official hook names: https://v2.tauri.app/distribute/windows-installer/

!macro NSIS_HOOK_PREINSTALL
!macroend

!macro NSIS_HOOK_POSTINSTALL
!macroend

!macro NSIS_HOOK_PREUNINSTALL
  DetailPrint "Hertzline: restore_all before uninstall"
  StrCpy $R9 ""
  IfFileExists "$INSTDIR\hertzline-helper.exe" 0 hertzline_try_resources
  StrCpy $R9 "$INSTDIR\hertzline-helper.exe"
  Goto hertzline_run_helper
  hertzline_try_resources:
  IfFileExists "$INSTDIR\resources\hertzline-helper.exe" 0 hertzline_try_ps1
  StrCpy $R9 "$INSTDIR\resources\hertzline-helper.exe"
  Goto hertzline_run_helper
  hertzline_run_helper:
  nsExec::ExecToLog '"$R9" restore_all --reason uninstall --json'
  Pop $0
  DetailPrint "hertzline-helper restore_all exit=$0"
  Goto hertzline_restore_done
  hertzline_try_ps1:
  IfFileExists "$INSTDIR\uninstall-restore.ps1" 0 hertzline_try_ps1_res
  nsExec::ExecToLog 'powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$INSTDIR\uninstall-restore.ps1"'
  Pop $0
  Goto hertzline_restore_done
  hertzline_try_ps1_res:
  IfFileExists "$INSTDIR\resources\uninstall-restore.ps1" 0 hertzline_restore_done
  nsExec::ExecToLog 'powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$INSTDIR\resources\uninstall-restore.ps1"'
  Pop $0
  hertzline_restore_done:
!macroend

!macro NSIS_HOOK_POSTUNINSTALL
!macroend
