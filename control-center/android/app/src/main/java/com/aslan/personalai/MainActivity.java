package com.aslan.personalai;

import android.os.Bundle;
import com.getcapacitor.BridgeActivity;

public class MainActivity extends BridgeActivity {
    @Override
    public void onCreate(Bundle savedInstanceState) {
        registerPlugin(SecureVaultPlugin.class);
        registerPlugin(ProtectedWebPlugin.class);
        registerPlugin(NativeAiPlugin.class);
        super.onCreate(savedInstanceState);
    }
}
