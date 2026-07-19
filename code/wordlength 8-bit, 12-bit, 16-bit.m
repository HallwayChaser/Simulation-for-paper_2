clc;
clear;
close all;

%% ==========================================================
% PARAMETERS
%% ==========================================================

Fs = 1000;              % Sampling frequency
N  = 256;               % FFT length

t = (0:N-1)/Fs;

%% ==========================================================
% INPUT SIGNAL
%% ==========================================================

x = sin(2*pi*50*t) + 0.6*sin(2*pi*120*t);

%% ==========================================================
% QUANTIZATION
%% ==========================================================

bits = [8 12 16];

scale8  = 2^(bits(1)-1)-1;
scale12 = 2^(bits(2)-1)-1;
scale16 = 2^(bits(3)-1)-1;

x8  = round(x*scale8)/scale8;
x12 = round(x*scale12)/scale12;
x16 = round(x*scale16)/scale16;

%% ==========================================================
% FFT
%% ==========================================================

FFT8  = abs(fft(x8));
FFT12 = abs(fft(x12));
FFT16 = abs(fft(x16));

%% ==========================================================
% FIGURE
%% ==========================================================

figure('Position',[80 80 1300 750]);

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
subplot(2,2,1)

plot(t,x,'k','LineWidth',2)
hold on
plot(t,x8,'r','LineWidth',1.8)

grid on
box on

xlim([0 0.1])
ylim([-2 2])

title('8-bit Quantization','FontSize',15,'FontWeight','bold')

xlabel('Time (s)')
ylabel('Amplitude')

legend('Original','8-bit')

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
subplot(2,2,2)

plot(t,x,'k','LineWidth',2)
hold on
plot(t,x12,'b','LineWidth',1.8)

grid on
box on

xlim([0 0.1])
ylim([-2 2])

title('12-bit Quantization','FontSize',15,'FontWeight','bold')

xlabel('Time (s)')
ylabel('Amplitude')

legend('Original','12-bit')

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
subplot(2,2,3)

plot(t,x,'k','LineWidth',2)
hold on
plot(t,x16,'g','LineWidth',1.8)

grid on
box on

xlim([0 0.1])
ylim([-2 2])

title('16-bit Quantization','FontSize',15,'FontWeight','bold')

xlabel('Time (s)')
ylabel('Amplitude')

legend('Original','16-bit')

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
subplot(2,2,4)

plot(FFT8,'r','LineWidth',2)
hold on

plot(FFT12,'b','LineWidth',2)

plot(FFT16,'g','LineWidth',2)

grid on
box on

xlim([0 N/2])

title('FFT Spectrum Comparison','FontSize',15,'FontWeight','bold')

xlabel('Frequency Bin')
ylabel('Magnitude')

legend('8-bit','12-bit','16-bit')

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
sgtitle('Word Length Simulation: 8-bit, 12-bit, and 16-bit',...
    'FontSize',20,...
    'FontWeight','bold')

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
annotation('textbox',...
[0.28 0.01 0.45 0.08],...
'String',...
sprintf(['FFT Length = %d    Sampling Frequency = %d Hz    Comparison of Word Lengths: 8 / 12 / 16 bits'],...
N,Fs),...
'HorizontalAlignment','center',...
'FontSize',11,...
'BackgroundColor','white',...
'EdgeColor','black');

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
exportgraphics(gcf,...
'WordLength_Comparison.png',...
'Resolution',300);