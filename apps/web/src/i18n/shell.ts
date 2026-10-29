export const en = {
  nav: {
    main: "Main",
    projects: "Projects",
    library: "Library",
    settings: "Settings",
    help: "Help",
    community: "Community",
    api: "API",
  },
  settings: {
    title: "Settings",
    theme: "Theme",
    light: "Light",
    dark: "Dark",
    server: "API server",
    serverNote: "Set with VITE_API_URL at build time. Every request goes to this server only.",
  },
  help: {
    title: "Help",
    make: "Make a part",
    makeBefore: "Open a project from ",
    makeAfter:
      ", describe the part with its sizes, and press Generate. Attach an image, a mesh or a spec file when the words are not enough. The timeline shows each step while the part is built and checked.",
    change: "Change it",
    changeText:
      "In the editor, edit a parameter and press Enter or Apply, or turn on Apply instantly. Select a component to aim a change request at it, or select a face to offset it. Every change is a new version; older ones can be restored.",
    context: "Give it context",
    contextText:
      "The Context tab of a project takes specs, tables, drawings and notes. Facts and rules found in them are used by every generation in that project and shown in the knowledge graph.",
    files: "Get the files",
    filesText:
      "Export STEP, STL, GLB or the build script from the editor, or share a read-only link to a version.",
  },
  bug: {
    open: "Report a bug",
    question: "What went wrong?",
    attach: "Attach a screenshot of the viewer",
    send: "Send",
    saved: "Thanks, the report was saved.",
    failed: (why: string) => `Could not send the report: ${why}`,
  },
};

export const de: typeof en = {
  nav: {
    main: "Hauptmenü",
    projects: "Projekte",
    library: "Bibliothek",
    settings: "Einstellungen",
    help: "Hilfe",
    community: "Community",
    api: "API",
  },
  settings: {
    title: "Einstellungen",
    theme: "Design",
    light: "Hell",
    dark: "Dunkel",
    server: "API-Server",
    serverNote: "Wird beim Build mit VITE_API_URL gesetzt. Jede Anfrage geht nur an diesen Server.",
  },
  help: {
    title: "Hilfe",
    make: "Ein Teil erstellen",
    makeBefore: "Öffne ein Projekt unter ",
    makeAfter:
      ", beschreibe das Teil mit seinen Maßen und drücke Generieren. Hänge ein Bild, ein Netz oder eine Spezifikation an, wenn Worte nicht reichen. Der Ablauf zeigt jeden Schritt, während das Teil erzeugt und geprüft wird.",
    change: "Ändern",
    changeText:
      "Ändere im Editor einen Parameter und drücke Enter oder Übernehmen, oder schalte Sofort übernehmen ein. Wähle ein Bauteil, um einen Änderungswunsch darauf zu richten, oder eine Fläche, um sie zu versetzen. Jede Änderung ist eine neue Version; ältere lassen sich wiederherstellen.",
    context: "Kontext geben",
    contextText:
      "Der Kontext-Reiter eines Projekts nimmt Spezifikationen, Tabellen, Zeichnungen und Notizen auf. Darin gefundene Fakten und Regeln nutzt jede Generierung im Projekt; der Wissensgraph zeigt sie.",
    files: "Dateien erhalten",
    filesText:
      "Exportiere STEP, STL, GLB oder das Build-Skript im Editor, oder teile einen Nur-Lese-Link zu einer Version.",
  },
  bug: {
    open: "Fehler melden",
    question: "Was ist schiefgelaufen?",
    attach: "Bildschirmfoto der Ansicht anhängen",
    send: "Senden",
    saved: "Danke, die Meldung wurde gespeichert.",
    failed: (why) => `Die Meldung konnte nicht gesendet werden: ${why}`,
  },
};
