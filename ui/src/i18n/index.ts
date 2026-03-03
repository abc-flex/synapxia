import en from "./en.json";
import es from "./es.json";

const translations = { en, es };

export const ui = { en, es }; // Export for client-side use

export type Locale = keyof typeof translations;

type NestedKeyOf<ObjectType extends object> = {
  [Key in keyof ObjectType & string]: ObjectType[Key] extends object
    ? `${Key}.${NestedKeyOf<ObjectType[Key]>}`
    : Key;
}[keyof ObjectType & string];

export type TranslationKey = NestedKeyOf<typeof en>;

const getNestedValue = (obj: any, path: string): string => {
  return path.split('.').reduce((current, key) => current?.[key], obj) ?? path;
}

export const t = (locale: Locale | string, key: string): string => {
  return getNestedValue(translations[locale as Locale], key);
}
