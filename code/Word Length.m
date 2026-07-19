clc;
clear;
close all;

%% =====================================================
% PARAMETERS
%% =====================================================

Fs = 1000;
f = 5;
t = 0:1/Fs:1;

x = sin(2*pi*f*t);

bits = [8 12 16];

%% =====================================================
% QUANTIZATION
%% =====================================================

Q8  = round(x*(2^(7)-1))/(2^(7)-1);
Q12 = round(x*(2^(11)-1))/(2^(11)-1);
Q16 = round(x*(2^(15)-1))/(2^(15)-1);

%% =====================================================
% SNR
%% =====================================================

Noise8  = x-Q8;
Noise12 = x-Q12;
Noise16 = x-Q16;

SNR = [...
10*log10(sum(x.^2)/sum(Noise8.^2)) ...
10*log10(sum(x.^2)/sum(Noise12.^2)) ...
10*log10(sum(x.^2)/sum(Noise16.^2))];

%% =====================================================
% EVM
%% =====================================================

EVM = [...
sqrt(mean(Noise8.^2)/mean(x.^2))*100 ...
sqrt(mean(Noise12.^2)/mean(x.^2))*100 ...
sqrt(mean(Noise16.^2)/mean(x.^2))*100];

%% =====================================================
% FIGURE
%% =====================================================

figure('Position',[80 80 1400 500]);

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% Quantization
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

subplot(1,3,1)

plot(t,x,'k','LineWidth',2.5)

hold on

stairs(t,Q8,'r','LineWidth',1.8)
stairs(t,Q12,'b','LineWidth',1.8)
stairs(t,Q16,'g','LineWidth',1.8)

grid on

title('Signal Quantization')

xlabel('Time (s)')
ylabel('Amplitude')

legend('Original',...
       '8-bit',...
       '12-bit',...
       '16-bit',...
       'Location','southwest')

set(gca,'FontSize',11,'LineWidth',1.5)

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% SNR
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

subplot(1,3,2)

plot(bits,SNR,...
'-o',...
'LineWidth',3,...
'MarkerSize',9,...
'MarkerFaceColor','b')

grid on

title('SNR')

xlabel('Word Length (bits)')
ylabel('SNR (dB)')

for i=1:3

text(bits(i),...
SNR(i)+0.8,...
sprintf('%.2f',SNR(i)),...
'HorizontalAlignment','center');

end

set(gca,'FontSize',11,'LineWidth',1.5)

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% EVM
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

subplot(1,3,3)

plot(bits,EVM,...
'-s',...
'LineWidth',3,...
'MarkerSize',9,...
'MarkerFaceColor','r')

grid on

title('EVM')

xlabel('Word Length (bits)')
ylabel('EVM (%)')

for i=1:3

text(bits(i),...
EVM(i)+0.1,...
sprintf('%.2f',EVM(i)),...
'HorizontalAlignment','center');

end

set(gca,'FontSize',11,'LineWidth',1.5)

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% Overall Title
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

sgtitle('Effect of Word Length on FFT Performance',...
'FontSize',18,...
'FontWeight','bold')

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% Formula
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

annotation('textbox',...
[0.34 0.01 0.34 0.08],...
'String',...
'SNR = 10log_{10}(P_s/P_n)      EVM = \surd(MSE/P_s)\times100%',...
'FontSize',12,...
'HorizontalAlignment','center',...
'EdgeColor','black',...
'BackgroundColor','white');

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% Export
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

exportgraphics(gcf,...
'WordLength_Comparison.png',...
'Resolution',300);