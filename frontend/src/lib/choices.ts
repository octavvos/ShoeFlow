// Backend'dagi TextChoices bilan bir xil qiymatlar (common/choices.py, customers/models.py)

export const REGIONS = [
  ["tashkent_city", "Toshkent shahri"],
  ["tashkent", "Toshkent viloyati"],
  ["andijan", "Andijon"],
  ["fergana", "Farg'ona"],
  ["namangan", "Namangan"],
  ["samarkand", "Samarqand"],
  ["bukhara", "Buxoro"],
  ["navoi", "Navoiy"],
  ["kashkadarya", "Qashqadaryo"],
  ["surkhandarya", "Surxondaryo"],
  ["jizzakh", "Jizzax"],
  ["syrdarya", "Sirdaryo"],
  ["khorezm", "Xorazm"],
  ["karakalpakstan", "Qoraqalpog'iston Respublikasi"],
] as const;

export const CUSTOMER_TYPES = [
  ["dealer", "Diler"],
  ["wholesale", "Ulgurji do'kon"],
  ["retail", "Chakana"],
  ["marketplace", "Marketpleys"],
] as const;

export const INTERACTION_TYPES = [
  ["call", "Qo'ng'iroq"],
  ["meeting", "Uchrashuv"],
  ["message", "Xabar"],
  ["note", "Izoh"],
] as const;

export const PAYMENT_METHODS = [
  ["cash", "Naqd"],
  ["card", "Plastik karta"],
  ["bank", "Bank o'tkazmasi"],
  ["click", "Click"],
  ["payme", "Payme"],
] as const;
