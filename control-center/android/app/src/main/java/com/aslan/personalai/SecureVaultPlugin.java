package com.aslan.personalai;

import android.content.Context;
import android.content.SharedPreferences;
import android.security.keystore.KeyGenParameterSpec;
import android.security.keystore.KeyProperties;
import android.util.Base64;
import com.getcapacitor.JSArray;
import com.getcapacitor.JSObject;
import com.getcapacitor.Plugin;
import com.getcapacitor.PluginCall;
import com.getcapacitor.PluginMethod;
import com.getcapacitor.annotation.CapacitorPlugin;
import java.nio.charset.StandardCharsets;
import java.security.KeyStore;
import java.util.Set;
import java.util.Arrays;
import java.util.HashSet;
import java.util.regex.Pattern;
import javax.crypto.Cipher;
import javax.crypto.KeyGenerator;
import javax.crypto.SecretKey;
import javax.crypto.spec.GCMParameterSpec;

@CapacitorPlugin(name = "SecureVault")
public class SecureVaultPlugin extends Plugin {
    private static final String KEYSTORE = "AndroidKeyStore";
    private static final String KEY_ALIAS = "project_one_provider_vault_v1";
    private static final String PREFS = "project_one_secure_vault_v1";
    private static final Pattern PROVIDER = Pattern.compile("^[a-z0-9_-]{1,32}$");
    private static final Set<String> ALLOWED_PROVIDERS = new HashSet<>(Arrays.asList("openai", "anthropic", "openrouter", "kimi", "google", "mistral", "xai"));
    private static final int MAX_SECRET_CHARS = 8192;

    private SharedPreferences prefs() {
        return getContext().getSharedPreferences(PREFS, Context.MODE_PRIVATE);
    }

    private String provider(PluginCall call) {
        String value = call.getString("provider", "");
        return PROVIDER.matcher(value).matches() && ALLOWED_PROVIDERS.contains(value) ? value : null;
    }

    private SecretKey masterKey() throws Exception {
        KeyStore store = KeyStore.getInstance(KEYSTORE);
        store.load(null);
        if (store.containsAlias(KEY_ALIAS)) return ((KeyStore.SecretKeyEntry) store.getEntry(KEY_ALIAS, null)).getSecretKey();
        KeyGenerator generator = KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES, KEYSTORE);
        generator.init(new KeyGenParameterSpec.Builder(KEY_ALIAS, KeyProperties.PURPOSE_ENCRYPT | KeyProperties.PURPOSE_DECRYPT)
            .setBlockModes(KeyProperties.BLOCK_MODE_GCM)
            .setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE)
            .setKeySize(256)
            .build());
        return generator.generateKey();
    }

    private String encrypt(String value) throws Exception {
        Cipher cipher = Cipher.getInstance("AES/GCM/NoPadding");
        cipher.init(Cipher.ENCRYPT_MODE, masterKey());
        byte[] encrypted = cipher.doFinal(value.getBytes(StandardCharsets.UTF_8));
        return Base64.encodeToString(cipher.getIV(), Base64.NO_WRAP) + "." + Base64.encodeToString(encrypted, Base64.NO_WRAP);
    }

    @PluginMethod
    public void storeSecret(PluginCall call) {
        String provider = provider(call);
        String secret = call.getString("secret", "");
        if (provider == null || secret.isEmpty() || secret.length() > MAX_SECRET_CHARS) { call.reject("invalid_input"); return; }
        try {
            prefs().edit().putString(provider, encrypt(secret)).apply();
            JSObject result = new JSObject(); result.put("stored", true); result.put("provider", provider); call.resolve(result);
        } catch (Exception error) { call.reject("vault_error"); }
    }

    @PluginMethod
    public void hasSecret(PluginCall call) {
        String provider = provider(call);
        if (provider == null) { call.reject("invalid_provider"); return; }
        JSObject result = new JSObject(); result.put("present", prefs().contains(provider)); result.put("provider", provider); call.resolve(result);
    }

    @PluginMethod
    public void deleteSecret(PluginCall call) {
        String provider = provider(call);
        if (provider == null) { call.reject("invalid_provider"); return; }
        prefs().edit().remove(provider).apply();
        JSObject result = new JSObject(); result.put("deleted", true); result.put("provider", provider); call.resolve(result);
    }

    @PluginMethod
    public void listProviders(PluginCall call) {
        Set<String> keys = prefs().getAll().keySet();
        JSArray providers = new JSArray();
        for (String key : keys) if (PROVIDER.matcher(key).matches() && ALLOWED_PROVIDERS.contains(key)) providers.put(key);
        JSObject result = new JSObject(); result.put("providers", providers); call.resolve(result);
    }
}
