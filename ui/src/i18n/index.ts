import en from "./en.json";
import es from "./es.json";

const translations = { en, es };

export type Locale = keyof typeof translations;

type NestedKeyOf<ObjectType extends object> = {
  [Key in keyof ObjectType & string]: ObjectType[Key] extends object
    ? `${Key}.${NestedKeyOf<ObjectType[Key]>}`
    : Key;
}[keyof ObjectType & string];

export type TranslationKey = NestedKeyOf<typeof en>;

function getNestedValue(obj: any, path: string): string {
  return path.split('.').reduce((current, key) => current?.[key], obj) ?? path;
}

export function t(locale: Locale, key: TranslationKey): string {
  return getNestedValue(translations[locale], key) ?? getNestedValue(translations.en, key);
}
