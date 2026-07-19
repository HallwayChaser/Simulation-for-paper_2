clc;
clear;
close all;

%% ============================================================
% PARAMETERS
%% ============================================================

Fs = 1000;                 % Sampling Frequency (Hz)
N  = 256;                  % FFT Length

t = (0:N-1)/Fs;

%% ============================================================
% INPUT SIGNAL
%% ============================================================

f1 = 50;
f2 = 120;

A1 = 1;
A2 = 0.6;

x = A1*sin(2*pi*f1*t) + A2*sin(2*pi*f2*t);

%% ============================================================
% FLOATING-POINT FFT
%% ============================================================

FFT_float = fft(x);
Mag_float = abs(FFT_float);

%% ============================================================
% FIXED-POINT FFT (8-bit)
%% ============================================================

bits = 8;

scale = 2^(bits-1)-1;

x_fixed = round(x*scale)/scale;

FFT_fixed = fft(x_fixed);
Mag_fixed = abs(FFT_fixed);

%% ============================================================
% FIGURE
%% ============================================================

figure('Position',[80 80 1300 750]);

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% Floating Signal
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

subplot(2,2,1)

plot(t,x,...
    'b',...
    'LineWidth',2.8)

grid on
box on

xlim([0 0.25])
ylim([-2 2])

title('Floating-point Signal',...
    'FontSize',16,...
    'FontWeight','bold')

xlabel('Time (s)',...
    'FontSize',13)

ylabel('Amplitude',...
    'FontSize',13)

set(gca,...
    'FontSize',12,...
    'LineWidth',1.5)

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% Fixed Signal
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

subplot(2,2,2)

plot(t,x_fixed,...
    'r',...
    'LineWidth',2.8)

grid on
box on

xlim([0 0.25])
ylim([-2 2])

title('Fixed-point Signal',...
    'FontSize',16,...
    'FontWeight','bold')

xlabel('Time (s)',...
    'FontSize',13)

ylabel('Amplitude',...
    'FontSize',13)

set(gca,...
    'FontSize',12,...
    'LineWidth',1.5)

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% Floating FFT
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

subplot(2,2,3)

plot(Mag_float,...
    'b',...
    'LineWidth',2.8)

grid on
box on

xlim([0 N])

title('Floating-point FFT',...
    'FontSize',16,...
    'FontWeight','bold')

xlabel('Frequency Bin',...
    'FontSize',13)

ylabel('Magnitude',...
    'FontSize',13)

set(gca,...
    'FontSize',12,...
    'LineWidth',1.5)

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% Fixed FFT
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

subplot(2,2,4)

plot(Mag_fixed,...
    'r',...
    'LineWidth',2.8)

grid on
box on

xlim([0 N])

title('Fixed-point FFT',...
    'FontSize',16,...
    'FontWeight','bold')

xlabel('Frequency Bin',...
    'FontSize',13)

ylabel('Magnitude',...
    'FontSize',13)

set(gca,...
    'FontSize',12,...
    'LineWidth',1.5)

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% Overall Title
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

sgtitle('Comparison between Floating-point and Fixed-point FFT',...
    'FontSize',22,...
    'FontWeight','bold')

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% INFORMATION BOX (Bottom Center)
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

annotation('textbox',...
[0.30 0.005 0.40 0.08],...
'String',...
sprintf(['FFT Length = %d        Sampling Frequency = %d Hz        Word Length = %d-bit'],...
N,Fs,bits),...
'HorizontalAlignment','center',...
'FontSize',12,...
'FontWeight','bold',...
'BackgroundColor','white',...
'EdgeColor','black');

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% EXPORT
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

exportgraphics(gcf,...
'Floating_vs_Fixed_FFT.png',...
'Resolution',300);