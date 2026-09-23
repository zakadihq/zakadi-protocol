/** One schema violation reported by a generated validator (Ajv's error object). */
export interface ValidationError {
  /** JSON Pointer to the failing value in the message; "" for the message. */
  instancePath: string;
  /** Location of the failing keyword in the schema. */
  schemaPath: string;
  /** The failing JSON Schema keyword, such as "required" or "enum". */
  keyword: string;
  /** Details of the failure, such as the missing property or the allowed values. */
  params: Record<string, unknown>;
  message?: string;
}

/**
 * A standalone validator generated from a message schema: a type guard over a
 * parsed JSON value. After each call, `errors` holds the violations it found, or
 * null when the value is valid.
 */
export interface Validator<T> {
  (data: unknown): data is T;
  errors?: ValidationError[] | null;
}
