; Zerobox NSIS Installer Hooks
; Detects and optionally installs Tesseract OCR and Ghostscript dependencies.
;
; For each missing dependency the user chooses one of:
;   - YES: Download and install system-wide (silent)
;   - NO: Download portable copy into the app's resources/ folder
;   - CANCEL: Skip (manual install later)

!include LogicLib.nsh

; ---------------------------------------------------------------------------
; Compatible version ranges and download URLs
; ---------------------------------------------------------------------------
!define TESSERACT_VERSION_RANGE "5.x (>= 5.0)"
!define TESSERACT_SETUP_URL "https://github.com/UB-Mannheim/tesseract/releases/download/v5.5.0.20241111/tesseract-ocr-w64-setup-5.5.0.20241111.exe"
!define TESSERACT_SETUP_FILE "tesseract-ocr-w64-setup.exe"

!define GS_VERSION_RANGE "9.50+ or 10.x"
!define GS_SETUP_URL "https://github.com/ArtifexSoftware/ghostpdl-downloads/releases/download/gs10050/gs10050w64.exe"
!define GS_SETUP_FILE "gs-setup.exe"

; ---------------------------------------------------------------------------
; Variables
; ---------------------------------------------------------------------------
Var TesseractFound
Var GhostscriptFound

; ---------------------------------------------------------------------------
; Detection: Tesseract OCR
; ---------------------------------------------------------------------------
!macro DetectTesseract
  StrCpy $TesseractFound "0"

  ; Check registry (UB-Mannheim installer)
  ReadRegStr $0 HKLM "SOFTWARE\Tesseract-OCR" "InstallDir"
  ${If} $0 != ""
    StrCpy $TesseractFound "1"
  ${EndIf}

  ; Check 32-bit registry view
  ${If} $TesseractFound == "0"
    SetRegView 32
    ReadRegStr $0 HKLM "SOFTWARE\Tesseract-OCR" "InstallDir"
    SetRegView 64
    ${If} $0 != ""
      StrCpy $TesseractFound "1"
    ${EndIf}
  ${EndIf}

  ; Check PATH
  ${If} $TesseractFound == "0"
    nsExec::ExecToStack 'where tesseract.exe'
    Pop $0
    Pop $1
    ${If} $0 == "0"
      StrCpy $TesseractFound "1"
    ${EndIf}
  ${EndIf}

  ; Check portable location from previous install
  ${If} $TesseractFound == "0"
    ${If} ${FileExists} "$INSTDIR\resources\tesseract\tesseract.exe"
      StrCpy $TesseractFound "1"
    ${EndIf}
  ${EndIf}
!macroend

; ---------------------------------------------------------------------------
; Detection: Ghostscript
; ---------------------------------------------------------------------------
!macro DetectGhostscript
  StrCpy $GhostscriptFound "0"

  ; Check registry (standard GS installer)
  EnumRegKey $0 HKLM "SOFTWARE\Artifex\GPL Ghostscript" 0
  ${If} $0 != ""
    StrCpy $GhostscriptFound "1"
  ${EndIf}

  ; Check 32-bit registry
  ${If} $GhostscriptFound == "0"
    SetRegView 32
    EnumRegKey $0 HKLM "SOFTWARE\Artifex\GPL Ghostscript" 0
    SetRegView 64
    ${If} $0 != ""
      StrCpy $GhostscriptFound "1"
    ${EndIf}
  ${EndIf}

  ; Check PATH
  ${If} $GhostscriptFound == "0"
    nsExec::ExecToStack 'where gswin64c.exe'
    Pop $0
    Pop $1
    ${If} $0 == "0"
      StrCpy $GhostscriptFound "1"
    ${EndIf}
  ${EndIf}

  ; Check portable location from previous install
  ${If} $GhostscriptFound == "0"
    ${If} ${FileExists} "$INSTDIR\resources\ghostscript\bin\gswin64c.exe"
      StrCpy $GhostscriptFound "1"
    ${EndIf}
  ${EndIf}
!macroend

; ---------------------------------------------------------------------------
; Prompt + install: Tesseract
; ---------------------------------------------------------------------------
!macro HandleTesseract
  ${If} $TesseractFound == "0"
    MessageBox MB_YESNOCANCEL|MB_ICONQUESTION \
      "Tesseract OCR was not found on this system.$\n$\n\
      It is required for document text extraction.$\n\
      Compatible versions: ${TESSERACT_VERSION_RANGE}$\n$\n\
      YES = Download and install system-wide$\n\
      NO = Download portable copy into Zerobox folder$\n\
      CANCEL = Skip (install manually later)" \
      IDYES tess_sysinstall IDNO tess_portable

    ; CANCEL — skip
    DetailPrint "Tesseract OCR: skipped by user"
    Goto tess_done

    tess_sysinstall:
      DetailPrint "Downloading Tesseract OCR..."
      NSISdl::download "${TESSERACT_SETUP_URL}" "$TEMP\${TESSERACT_SETUP_FILE}"
      Pop $0
      ${If} $0 == "success"
        DetailPrint "Installing Tesseract OCR (system-wide)..."
        nsExec::ExecToLog '"$TEMP\${TESSERACT_SETUP_FILE}" /S'
        Pop $0
        Delete "$TEMP\${TESSERACT_SETUP_FILE}"
        ${If} $0 == "0"
          DetailPrint "Tesseract OCR installed successfully."
        ${Else}
          DetailPrint "Tesseract installer exit code: $0"
          MessageBox MB_OK|MB_ICONEXCLAMATION \
            "Tesseract installation may have failed (exit code: $0).$\n\
            Please verify the installation or install manually."
        ${EndIf}
      ${Else}
        DetailPrint "Tesseract download failed: $0"
        MessageBox MB_OK|MB_ICONEXCLAMATION \
          "Failed to download Tesseract OCR.$\n\
          Please install manually.$\nCompatible versions: ${TESSERACT_VERSION_RANGE}"
      ${EndIf}
      Goto tess_done

    tess_portable:
      DetailPrint "Downloading Tesseract OCR (portable)..."
      NSISdl::download "${TESSERACT_SETUP_URL}" "$TEMP\${TESSERACT_SETUP_FILE}"
      Pop $0
      ${If} $0 == "success"
        DetailPrint "Extracting Tesseract to resources folder..."
        CreateDirectory "$INSTDIR\resources\tesseract"
        nsExec::ExecToLog '"$TEMP\${TESSERACT_SETUP_FILE}" /S /D=$INSTDIR\resources\tesseract'
        Pop $0
        Delete "$TEMP\${TESSERACT_SETUP_FILE}"
        ${If} $0 == "0"
          DetailPrint "Tesseract OCR installed to $INSTDIR\resources\tesseract"
        ${Else}
          DetailPrint "Tesseract extraction exit code: $0"
          MessageBox MB_OK|MB_ICONEXCLAMATION \
            "Tesseract portable extraction may have failed.$\n\
            Please verify or install manually."
        ${EndIf}
      ${Else}
        DetailPrint "Tesseract download failed: $0"
        MessageBox MB_OK|MB_ICONEXCLAMATION \
          "Failed to download Tesseract OCR.$\n\
          Please install manually.$\nCompatible versions: ${TESSERACT_VERSION_RANGE}"
      ${EndIf}

    tess_done:
  ${EndIf}
!macroend

; ---------------------------------------------------------------------------
; Prompt + install: Ghostscript
; ---------------------------------------------------------------------------
!macro HandleGhostscript
  ${If} $GhostscriptFound == "0"
    MessageBox MB_YESNOCANCEL|MB_ICONQUESTION \
      "Ghostscript was not found on this system.$\n$\n\
      It is required for PDF processing.$\n\
      Compatible versions: ${GS_VERSION_RANGE}$\n$\n\
      YES = Download and install system-wide$\n\
      NO = Download portable copy into Zerobox folder$\n\
      CANCEL = Skip (install manually later)" \
      IDYES gs_sysinstall IDNO gs_portable

    ; CANCEL — skip
    DetailPrint "Ghostscript: skipped by user"
    Goto gs_done

    gs_sysinstall:
      DetailPrint "Downloading Ghostscript..."
      NSISdl::download "${GS_SETUP_URL}" "$TEMP\${GS_SETUP_FILE}"
      Pop $0
      ${If} $0 == "success"
        DetailPrint "Installing Ghostscript (system-wide)..."
        nsExec::ExecToLog '"$TEMP\${GS_SETUP_FILE}" /S'
        Pop $0
        Delete "$TEMP\${GS_SETUP_FILE}"
        ${If} $0 == "0"
          DetailPrint "Ghostscript installed successfully."
        ${Else}
          DetailPrint "Ghostscript installer exit code: $0"
          MessageBox MB_OK|MB_ICONEXCLAMATION \
            "Ghostscript installation may have failed (exit code: $0).$\n\
            Please verify the installation or install manually."
        ${EndIf}
      ${Else}
        DetailPrint "Ghostscript download failed: $0"
        MessageBox MB_OK|MB_ICONEXCLAMATION \
          "Failed to download Ghostscript.$\n\
          Please install manually.$\nCompatible versions: ${GS_VERSION_RANGE}"
      ${EndIf}
      Goto gs_done

    gs_portable:
      DetailPrint "Downloading Ghostscript (portable)..."
      NSISdl::download "${GS_SETUP_URL}" "$TEMP\${GS_SETUP_FILE}"
      Pop $0
      ${If} $0 == "success"
        DetailPrint "Extracting Ghostscript to resources folder..."
        CreateDirectory "$INSTDIR\resources\ghostscript"
        nsExec::ExecToLog '"$TEMP\${GS_SETUP_FILE}" /S /D=$INSTDIR\resources\ghostscript'
        Pop $0
        Delete "$TEMP\${GS_SETUP_FILE}"
        ${If} $0 == "0"
          DetailPrint "Ghostscript installed to $INSTDIR\resources\ghostscript"
        ${Else}
          DetailPrint "Ghostscript extraction exit code: $0"
          MessageBox MB_OK|MB_ICONEXCLAMATION \
            "Ghostscript portable extraction may have failed.$\n\
            Please verify or install manually."
        ${EndIf}
      ${Else}
        DetailPrint "Ghostscript download failed: $0"
        MessageBox MB_OK|MB_ICONEXCLAMATION \
          "Failed to download Ghostscript.$\n\
          Please install manually.$\nCompatible versions: ${GS_VERSION_RANGE}"
      ${EndIf}

    gs_done:
  ${EndIf}
!macroend

; ---------------------------------------------------------------------------
; PREINSTALL hook — called by Tauri's installer.nsi
; ---------------------------------------------------------------------------
!macro NSIS_HOOK_PREINSTALL
  !insertmacro DetectTesseract
  !insertmacro DetectGhostscript
  !insertmacro HandleTesseract
  !insertmacro HandleGhostscript
!macroend
