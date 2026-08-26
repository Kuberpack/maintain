export type Locale = 'en' | 'hi'

type Msg = {
  today: string
  late: string
  dueToday: string
  waiting: string
  start: string
  ok: string
  problem: string
  stop: string
  later: string
  next: string
  back: string
  submit: string
  photo: string
  extraPhoto: string
  retake: string
  reading: string
  notes: string
  required: string
  rejectReason: string
  nothingToday: string
  saving: string
  repairOpen: string
  handover: string
  logout: string
  loading: string
  machines: string
  review: string
  overdue: string
  summary: string
  reports: string
  users: string
  profile: string
  signIn: string
  phone: string
  pin: string
  email: string
  password: string
  phonePin: string
  emailPassword: string
  loginFailed: string
  noOperator: string
  assignedOperator: string
  unassigned: string
  machineNote: string
  saveNote: string
  noNoteYet: string
  machineDetails: string
  languageEn: string
  languageHi: string
  directory: string
  noContacts: string
  call: string
  whatsapp: string
  allMachines: string
  reportRepair: string
  logReplacement: string
  repairImpact: string
  repairImpactHint: string
  issueDescription: string
  downtimeMinutes: string
  partName: string
  replacedOn: string
  myMachine: string
  shift: string
  shiftLog: string
  shiftLogSaved: string
  startTime: string
  endTime: string
  runningHours: string
  output: string
  jobChanges: string
  wastageBoardline: string
  wastageMachine: string
  delayReason: string
  delayMinutes: string
  save: string
  cancel: string
  optional: string
}

export const messages: Record<Locale, Msg> = {
  en: {
    today: "Today’s work",
    late: 'Late',
    dueToday: 'Due today',
    waiting: 'Waiting for supervisor',
    start: 'Start',
    ok: 'OK',
    problem: 'Problem',
    stop: 'Stop',
    later: 'Later',
    next: 'Next',
    back: 'Back',
    submit: 'Send to supervisor',
    photo: 'Take machine photo',
    extraPhoto: 'Take photo of the problem',
    retake: 'Retake',
    reading: 'Reading',
    notes: 'Note',
    required: 'Required',
    rejectReason: 'Supervisor said',
    nothingToday: 'Nothing left today',
    saving: 'Saving…',
    repairOpen: 'Open repair',
    handover: 'Note on this machine',
    logout: 'Log out',
    loading: 'Loading…',
    machines: 'Machines',
    review: 'Review',
    overdue: 'Overdue',
    summary: 'Summary',
    reports: 'Reports',
    users: 'Users',
    profile: 'My Profile',
    signIn: 'Sign in',
    phone: 'Phone number',
    pin: 'PIN',
    email: 'Email',
    password: 'Password',
    phonePin: 'Phone + PIN',
    emailPassword: 'Email + Password',
    loginFailed: 'Login failed',
    noOperator: 'No operator assigned',
    assignedOperator: 'Operator',
    unassigned: 'Unassigned',
    machineNote: 'Note on this machine',
    saveNote: 'Save note',
    noNoteYet: 'No note yet.',
    machineDetails: 'Machine details',
    languageEn: 'EN',
    languageHi: 'हिं',
    directory: 'Help numbers',
    noContacts: 'No outside contacts yet.',
    call: 'Call',
    whatsapp: 'WhatsApp',
    allMachines: 'All machines',
    reportRepair: 'Report a repair',
    logReplacement: 'Log a part replacement',
    repairImpact: 'What will this cause?',
    repairImpactHint: 'e.g. feeder is down, no printing this shift',
    issueDescription: 'What is wrong?',
    downtimeMinutes: 'Downtime, minutes',
    partName: 'Part name',
    replacedOn: 'Replaced on',
    myMachine: 'My machine',
    shift: 'Shift',
    shiftLog: "Today's shift log",
    shiftLogSaved: 'Shift log saved',
    startTime: 'Start time',
    endTime: 'End time',
    runningHours: 'Running hours',
    output: 'Total output',
    jobChanges: 'Job changes',
    wastageBoardline: 'Wastage — board line',
    wastageMachine: 'Wastage — machine',
    delayReason: 'Reason of delay',
    delayMinutes: 'Delay, minutes',
    save: 'Save',
    cancel: 'Cancel',
    optional: 'optional',
  },
  hi: {
    today: 'आज का काम',
    late: 'लेट',
    dueToday: 'आज करना है',
    waiting: 'सुपरवाइज़र देख रहे हैं',
    start: 'शुरू करें',
    ok: 'ठीक है',
    problem: 'ध्यान दो',
    stop: 'खराब',
    later: 'बाद में',
    next: 'आगे',
    back: 'पीछे',
    submit: 'सुपरवाइज़र को भेजें',
    photo: 'मशीन की फोटो लें',
    extraPhoto: 'समस्या की फोटो लें',
    retake: 'फिर से फोटो',
    reading: 'पढ़ाव',
    notes: 'नोट',
    required: 'ज़रूरी',
    rejectReason: 'सुपरवाइज़र ने कहा',
    nothingToday: 'आज कोई काम बाकी नहीं',
    saving: 'सेव हो रहा है…',
    repairOpen: 'मरम्मत खुली है',
    handover: 'मशीन पर नोट',
    logout: 'लॉग आउट',
    loading: 'लोड हो रहा है…',
    machines: 'मशीनें',
    review: 'रिव्यू',
    overdue: 'लेट',
    summary: 'सारांश',
    reports: 'रिपोर्ट',
    users: 'यूज़र',
    profile: 'मेरी प्रोफ़ाइल',
    signIn: 'साइन इन',
    phone: 'फ़ोन नंबर',
    pin: 'पिन',
    email: 'ईमेल',
    password: 'पासवर्ड',
    phonePin: 'फ़ोन + पिन',
    emailPassword: 'ईमेल + पासवर्ड',
    loginFailed: 'लॉगिन नहीं हुआ',
    noOperator: 'कोई ऑपरेटर नहीं',
    assignedOperator: 'ऑपरेटर',
    unassigned: 'असाइन नहीं',
    machineNote: 'मशीन पर नोट',
    saveNote: 'नोट सेव करें',
    noNoteYet: 'अभी कोई नोट नहीं।',
    machineDetails: 'मशीन की जानकारी',
    languageEn: 'EN',
    languageHi: 'हिं',
    directory: 'मदद के नंबर',
    noContacts: 'अभी कोई बाहरी नंबर नहीं।',
    call: 'कॉल करें',
    whatsapp: 'व्हाट्सएप',
    allMachines: 'सभी मशीनें',
    reportRepair: 'मरम्मत दर्ज करें',
    logReplacement: 'पार्ट बदलना दर्ज करें',
    repairImpact: 'इससे क्या रुकेगा?',
    repairImpactHint: 'जैसे: फीडर बंद है, इस शिफ्ट में छपाई नहीं होगी',
    issueDescription: 'क्या खराबी है?',
    downtimeMinutes: 'मशीन बंद रही, मिनट',
    partName: 'पार्ट का नाम',
    replacedOn: 'कब बदला',
    myMachine: 'मेरी मशीन',
    shift: 'शिफ्ट',
    shiftLog: 'आज का शिफ्ट लॉग',
    shiftLogSaved: 'शिफ्ट लॉग सेव हो गया',
    startTime: 'शुरू का समय',
    endTime: 'बंद का समय',
    runningHours: 'चलने के घंटे',
    output: 'कुल उत्पादन',
    jobChanges: 'जॉब चेंज',
    wastageBoardline: 'बर्बादी — बोर्ड लाइन',
    wastageMachine: 'बर्बादी — मशीन',
    delayReason: 'देरी का कारण',
    delayMinutes: 'देरी, मिनट',
    save: 'सेव करें',
    cancel: 'रद्द करें',
    optional: 'ज़रूरी नहीं',
  },
}

export const STORAGE_KEY = 'kuberpack.locale'

/** @deprecated Use useLocale().t — kept so leftover imports still type-check during the switch. */
export const hi = messages.hi
