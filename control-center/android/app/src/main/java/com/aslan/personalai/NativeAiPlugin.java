package com.aslan.personalai;

import android.content.Context;
import android.content.SharedPreferences;
import android.security.keystore.KeyProperties;
import android.util.Base64;
import com.getcapacitor.JSObject;
import com.getcapacitor.Plugin;
import com.getcapacitor.PluginCall;
import com.getcapacitor.PluginMethod;
import com.getcapacitor.annotation.CapacitorPlugin;
import java.io.BufferedReader;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.security.KeyStore;
import java.util.regex.Pattern;
import java.util.concurrent.atomic.AtomicBoolean;
import javax.crypto.Cipher;
import javax.crypto.SecretKey;
import javax.crypto.spec.GCMParameterSpec;
import org.json.JSONArray;
import org.json.JSONObject;

@CapacitorPlugin(name = "NativeAi")
public class NativeAiPlugin extends Plugin {
    private static final String KEYSTORE = "AndroidKeyStore";
    private static final String KEY_ALIAS = "project_one_provider_vault_v1";
    private static final String PREFS = "project_one_secure_vault_v1";
    private static final Pattern MODEL = Pattern.compile("^[A-Za-z0-9._-]{1,80}$");
    private static final int MAX_PROMPT = 16000;
    private static final int MAX_RESPONSE = 1000000;
    private static final int MAX_OUTPUT_TOKENS = 4096;
    private final AtomicBoolean requestInFlight = new AtomicBoolean(false);

    @PluginMethod
    public void capabilities(PluginCall call) {
        JSObject out = new JSObject();
        out.put("mistral", has("mistral"));
        out.put("xai", has("xai"));
        out.put("google", has("google"));
        call.resolve(out);
    }

    @PluginMethod
    public void generate(PluginCall call) {
        String provider = call.getString("provider", "");
        String model = call.getString("model", "");
        String prompt = call.getString("prompt", "");
        if (!(provider.equals("mistral") || provider.equals("xai") || provider.equals("google")) || !MODEL.matcher(model).matches() || prompt.isEmpty() || prompt.length() > MAX_PROMPT) {
            call.reject("invalid_input"); return;
        }
        if (!allowedModel(provider, model)) { call.reject("model_not_allowed"); return; }
        if (!has(provider)) { call.reject("provider_not_configured"); return; }
        if (!requestInFlight.compareAndSet(false, true)) { call.reject("request_already_in_flight"); return; }
        getBridge().executeOnMainThread(() -> new Thread(() -> request(call, provider, model, prompt)).start());
    }


    private boolean allowedModel(String provider, String model) {
        if (provider.equals("google")) return model.equals("gemini-2.5-flash");
        if (provider.equals("mistral")) return model.equals("mistral-small-latest");
        if (provider.equals("xai")) return model.equals("grok-4.6");
        return false;
    }

    private boolean has(String provider) { return prefs().contains(provider); }
    private SharedPreferences prefs() { return getContext().getSharedPreferences(PREFS, Context.MODE_PRIVATE); }

    private String secret(String provider) throws Exception {
        String packed = prefs().getString(provider, null);
        if (packed == null) throw new IllegalStateException("missing_secret");
        String[] parts = packed.split("\\.", 2);
        if (parts.length != 2) throw new IllegalStateException("bad_secret");
        KeyStore ks = KeyStore.getInstance(KEYSTORE); ks.load(null);
        SecretKey key = ((KeyStore.SecretKeyEntry) ks.getEntry(KEY_ALIAS, null)).getSecretKey();
        Cipher cipher = Cipher.getInstance("AES/GCM/NoPadding");
        cipher.init(Cipher.DECRYPT_MODE, key, new GCMParameterSpec(128, Base64.decode(parts[0], Base64.NO_WRAP)));
        return new String(cipher.doFinal(Base64.decode(parts[1], Base64.NO_WRAP)), StandardCharsets.UTF_8);
    }

    private void request(PluginCall call, String provider, String model, String prompt) {
        HttpURLConnection conn = null;
        try {
            String apiKey = secret(provider);
            String endpoint;
            JSONObject body = new JSONObject();
            if (provider.equals("google")) {
                endpoint = "https://generativelanguage.googleapis.com/v1beta/models/" + model + ":generateContent";
                JSONArray contents = new JSONArray();
                JSONObject user = new JSONObject(); user.put("role", "user");
                user.put("parts", new JSONArray().put(new JSONObject().put("text", prompt)));
                contents.put(user); body.put("contents", contents);
                body.put("generationConfig", new JSONObject().put("maxOutputTokens", MAX_OUTPUT_TOKENS));
            } else {
                endpoint = provider.equals("mistral") ? "https://api.mistral.ai/v1/chat/completions" : "https://api.x.ai/v1/chat/completions";
                body.put("model", model);
                body.put("messages", new JSONArray().put(new JSONObject().put("role", "user").put("content", prompt)));
                body.put("max_tokens", MAX_OUTPUT_TOKENS);
            }
            conn = (HttpURLConnection) new URL(endpoint).openConnection();
            conn.setRequestMethod("POST"); conn.setConnectTimeout(15000); conn.setReadTimeout(60000);
            conn.setInstanceFollowRedirects(false); conn.setDoOutput(true);
            conn.setRequestProperty("Content-Type", "application/json");
            if (provider.equals("google")) conn.setRequestProperty("x-goog-api-key", apiKey);
            else conn.setRequestProperty("Authorization", "Bearer " + apiKey);
            byte[] bytes = body.toString().getBytes(StandardCharsets.UTF_8);
            conn.setFixedLengthStreamingMode(bytes.length);
            try (OutputStream os = conn.getOutputStream()) { os.write(bytes); }
            int status = conn.getResponseCode();
            InputStream stream = status >= 200 && status < 300 ? conn.getInputStream() : conn.getErrorStream();
            String raw = readLimited(stream);
            if (status < 200 || status >= 300) { call.reject("provider_http_" + status); return; }
            JSONObject json = new JSONObject(raw);
            String text;
            if (provider.equals("google")) text = json.getJSONArray("candidates").getJSONObject(0).getJSONObject("content").getJSONArray("parts").getJSONObject(0).optString("text", "");
            else text = json.getJSONArray("choices").getJSONObject(0).getJSONObject("message").optString("content", "");
            JSObject result = new JSObject(); result.put("provider", provider); result.put("model", model); result.put("text", text); call.resolve(result);
        } catch (Exception error) { call.reject("provider_request_failed"); }
        finally { if (conn != null) conn.disconnect(); requestInFlight.set(false); }
    }

    private String readLimited(InputStream stream) throws Exception {
        if (stream == null) return "";
        StringBuilder out = new StringBuilder(); char[] buf = new char[4096]; int n;
        try (BufferedReader reader = new BufferedReader(new InputStreamReader(stream, StandardCharsets.UTF_8))) {
            while ((n = reader.read(buf)) != -1) { if (out.length() + n > MAX_RESPONSE) throw new IllegalStateException("response_too_large"); out.append(buf, 0, n); }
        }
        return out.toString();
    }
}
