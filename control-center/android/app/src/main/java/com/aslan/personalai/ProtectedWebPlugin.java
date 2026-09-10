package com.aslan.personalai;

import android.content.Intent;
import com.getcapacitor.JSObject;
import com.getcapacitor.Plugin;
import com.getcapacitor.PluginCall;
import com.getcapacitor.PluginMethod;
import com.getcapacitor.annotation.CapacitorPlugin;
import java.util.Arrays;
import java.util.HashSet;
import java.util.Set;

@CapacitorPlugin(name = "ProtectedWeb")
public class ProtectedWebPlugin extends Plugin {
    private static final Set<String> SERVICES = new HashSet<>(Arrays.asList("github", "pocketoption"));

    @PluginMethod
    public void open(PluginCall call) {
        String service = call.getString("service", "");
        if (!SERVICES.contains(service)) { call.reject("service_not_allowed"); return; }
        Intent intent = new Intent(getContext(), ProtectedWebActivity.class);
        intent.putExtra(ProtectedWebActivity.EXTRA_SERVICE, service);
        getActivity().startActivity(intent);
        JSObject result = new JSObject(); result.put("opened", true); call.resolve(result);
    }
}
