clc;
clear;
close all;

%% ======================================================
% Parameters
%% ======================================================

Fs = 1000;              % Sampling Frequency
N  = 256;               % FFT Length

t = (0:N-1)/Fs;

%% Input Signal

x = sin(2*pi*50*t) + 0.6*sin(2*pi*120*t);

%% Floating-point FFT

FFT_float = fft(x);

%% Fixed-point Quantization (8-bit)

bits = 8;

scale = 2^(bits-1)-1;

x_fixed = round(x*scale)/scale;

FFT_fixed = fft(x_fixed);

%% Magnitude

Mag_float = abs(FFT_float);

Mag_fixed = abs(FFT_fixed);

%% ======================================================
% Figure
%% ======================================================

figure('Position',[100 100 1200 700]);

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
subplot(2,2,1)

plot(t,x,'b','LineWidth',2)

grid on

title('Floating-point Signal')

xlabel('Time (s)')
ylabel('Amplitude')

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
subplot(2,2,2)

plot(t,x_fixed,'r','LineWidth',2)

grid on

title('Fixed-point Signal')

xlabel('Time (s)')
ylabel('Amplitude')

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
subplot(2,2,3)

plot(Mag_float,'b','LineWidth',2)

grid on

title('Floating-point FFT')

xlabel('Frequency Bin')
ylabel('Magnitude')

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
subplot(2,2,4)

plot(Mag_fixed,'r','LineWidth',2)

grid on

title('Fixed-point FFT')

xlabel('Frequency Bin')
ylabel('Magnitude')

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

sgtitle('Comparison between Floating-point and Fixed-point FFT',...
    'FontSize',18,...
    'FontWeight','bold');

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

annotation('textbox',...
[0.68 0.70 0.27 0.18],...
'String',...
sprintf(['FFT Length = %d\n\nSampling = %d Hz\n\nWord Length = %d-bit'],...
N,Fs,bits),...
'FontSize',12,...
'BackgroundColor','white',...
'EdgeColor','black');

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

exportgraphics(gcf,...
'Floating_vs_Fixed_FFT.png',...
'Resolution',300);