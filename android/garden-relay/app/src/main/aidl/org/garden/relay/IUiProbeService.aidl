package org.garden.relay;

interface IUiProbeService {
    void destroy() = 16777114;
    String probeDeepSeekInput() = 1;
    String calibrateDeepSeekTap(int width, int height) = 2;
}
