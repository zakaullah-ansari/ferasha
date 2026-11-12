/**
 * The browser's copy of Django's account rules, the email typo helper, and
 * "Keep me signed in" (session-only cookies that survive token rotation).
 */

import { NextResponse } from "next/server";
import { describe, expect, it } from "vitest";

import { fieldIssues, passwordRules, registerSchema, signInSchema, suggestEmail } from "@/lib/auth-validation";
import { ACCESS_COOKIE, REFRESH_COOKIE, SESSION_ONLY_COOKIE, writeSessionCookies } from "@/lib/session";

const VALID = { full_name: "Ayesha Khan", email: "ayesha@example.com", password: "Correct-Horse-9182", accept_terms: true };

describe("registration rules mirror Django's", () => {
  it("accepts a complete, sensible registration", () => {
    expect(fieldIssues(registerSchema, VALID)).toEqual({});
  });

  it.each([
    [{ full_name: "   " }, "full_name", "Enter your full name."],
    [{ email: "ayesha" }, "email", "Enter a valid email address, like name@example.com."],
    [{ email: "" }, "email", "Enter your email address."],
    [{ password: "short" }, "password", "Use at least 10 characters."],
    [{ password: "1234567890" }, "password", "Use letters or symbols too, not only numbers."],
    [{ accept_terms: false }, "accept_terms", "Please accept the terms to create an account."],
  ])("%o -> %s", (change, field, message) => {
    expect(fieldIssues(registerSchema, { ...VALID, ...change })[field]).toBe(message);
  });

  it("does not refuse what Django would accept (name inside the password)", () => {
    expect(fieldIssues(registerSchema, { ...VALID, password: "Ayesha-Correct-9182" })).toEqual({});
  });

  it("reports a weak password even while other fields are still empty", () => {
    const issues = fieldIssues(registerSchema, { full_name: "", email: "", password: "short", accept_terms: false });
    expect(issues.password).toBe("Use at least 10 characters.");
  });

  it("trims the email before checking it", () => {
    expect(fieldIssues(signInSchema, { email: "  ayesha@example.com ", password: "x" })).toEqual({});
  });

  it("reports the live checklist", () => {
    expect(passwordRules("").map((rule) => rule.met)).toEqual([false, false]);
    expect(passwordRules("1234567890").map((rule) => rule.met)).toEqual([true, false]);
    expect(passwordRules("Correct-Horse-9182").map((rule) => rule.met)).toEqual([true, true]);
  });
});

describe("email typo help", () => {
  it.each([
    ["ayesha@gmial.com", "ayesha@gmail.com"],
    ["ayesha@gmail.con", "ayesha@gmail.com"],
    ["ayesha@yaho.co.in", "ayesha@yahoo.co.in"],
    ["Ayesha@Hotmial.com", "ayesha@hotmail.com"],
  ])("%s -> %s", (typed, suggested) => {
    expect(suggestEmail(typed)).toBe(suggested);
  });

  it.each(["ayesha@gmail.com", "ayesha@kausar.in", "ayesha@", "no-at-sign", "a@b.io"])("leaves %s alone", (typed) => {
    expect(suggestEmail(typed)).toBeNull();
  });
});

describe("keep me signed in", () => {
  const pair = { access: "a.b.c", refresh: "d.e.f" };

  it("remembers by default: cookies carry an expiry", () => {
    const response = NextResponse.json({});
    writeSessionCookies(response, pair);
    expect(response.cookies.get(ACCESS_COOKIE)?.maxAge).toBeGreaterThan(0);
    expect(response.cookies.get(SESSION_ONLY_COOKIE)?.value ?? "").toBe("");
  });

  it("un-ticked: browser-session cookies, plus the marker the refresh path reads", () => {
    const response = NextResponse.json({});
    writeSessionCookies(response, pair, { persistent: false });
    expect(response.cookies.get(ACCESS_COOKIE)?.maxAge).toBeUndefined();
    expect(response.cookies.get(REFRESH_COOKIE)?.maxAge).toBeUndefined();
    expect(response.cookies.get(REFRESH_COOKIE)?.httpOnly).toBe(true);
    expect(response.cookies.get(SESSION_ONLY_COOKIE)?.value).toBe("1");
    expect(response.cookies.get(SESSION_ONLY_COOKIE)?.maxAge).toBeUndefined();
  });
});
