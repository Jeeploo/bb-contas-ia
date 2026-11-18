// Mapa do Brasil simplificado (5 regiões) em SVG inline, sem dependências externas.
// Contornos aproximados, apenas ilustrativos.
type Regiao = 'Norte' | 'Nordeste' | 'Centro-Oeste' | 'Sudeste' | 'Sul';

const REGIOES: Record<Regiao, string> = {
  'Norte': '0.5,61.5 5,47.5 20,46 22.5,20 35,20 50,5 67.5,2 80,17.5 100,14 115,3 120,25 130,30 140,30 130,50 140,70 140,90 117.5,90 117.5,72.5 80,62.5 62.5,67.5 70,92.5 43.5,74 20,80',
  'Nordeste': '140,30 165,39.5 180,43.5 194,51 196,62.5 187.5,77.5 177.5,90 175,114.5 171.5,116.5 165,105 150,100 140,100 140,90 140,70 130,50',
  'Centro-Oeste': '62.5,67.5 80,62.5 117.5,72.5 117.5,90 140,90 140,100 135,102.5 115,122.5 115,125 105,138 97,145 91.5,137.5 81,135 80,125 80,106.5 70,92.5',
  'Sudeste': '140,100 150,100 165,105 171.5,116.5 167.5,130 160,140 147.5,141 137.5,145 130,151 120,139.5 105,138 115,125 115,122.5 135,102.5',
  'Sul': '105,138 120,139.5 130,151 127.5,167.5 117.5,179 103,193.5 82,176 101,161 97,153 97,145',
};

// UF → região e posição aproximada do estado no viewBox.
const UFS: Record<string, [Regiao, number, number]> = {
  AC: ['Norte', 20, 70], AM: ['Norte', 50, 45], RR: ['Norte', 65, 15], PA: ['Norte', 107.5, 45], AP: ['Norte', 112.5, 17.5], RO: ['Norte', 55, 80], TO: ['Norte', 128.5, 75],
  MA: ['Nordeste', 145, 50], PI: ['Nordeste', 157.5, 62.5], CE: ['Nordeste', 172.5, 50], RN: ['Nordeste', 187.5, 54], PB: ['Nordeste', 187.5, 60.5], PE: ['Nordeste', 182.5, 67], AL: ['Nordeste', 187.5, 73], SE: ['Nordeste', 183, 78], BA: ['Nordeste', 161.5, 87.5],
  MT: ['Centro-Oeste', 90, 90], GO: ['Centro-Oeste', 122, 105], DF: ['Centro-Oeste', 130.5, 104], MS: ['Centro-Oeste', 97.5, 127.5],
  MG: ['Sudeste', 147.5, 117.5], ES: ['Sudeste', 167.5, 123], RJ: ['Sudeste', 156.5, 136.5], SP: ['Sudeste', 127.5, 136.5],
  PR: ['Sul', 112.5, 148], SC: ['Sul', 117.5, 161.5], RS: ['Sul', 102.5, 174],
};

export function regiaoDaUf(uf?: string): Regiao | undefined {
  return uf ? UFS[uf.trim().toUpperCase()]?.[0] : undefined;
}

export function MapaRegiao({ cidade, uf }: { cidade?: string; uf?: string }) {
  const info = uf ? UFS[uf.trim().toUpperCase()] : undefined;
  const regiao = info?.[0];
  const local = [cidade, uf?.toUpperCase()].filter(Boolean).join(' - ');
  return (
    <figure className="mapa-regiao">
      <svg viewBox="-4 -4 208 202" role="img" aria-label={regiao ? `Mapa do Brasil com a região ${regiao} destacada` : 'Mapa do Brasil'}>
        {(Object.keys(REGIOES) as Regiao[]).map(r => (
          <polygon key={r} points={REGIOES[r]} fill={r === regiao ? '#FFE600' : '#FFFFFF'} stroke="#B9C2CF" strokeWidth="1.2" strokeLinejoin="round" />
        ))}
        {info && <>
          <circle cx={info[1]} cy={info[2]} r="7" fill="#E0B400" opacity="0.35" />
          <circle cx={info[1]} cy={info[2]} r="3.6" fill="#C79A00" stroke="#FFFFFF" strokeWidth="1.2" />
        </>}
      </svg>
      <figcaption>
        <strong>{local || 'Localidade não informada'}</strong>
        {regiao && <span>{regiao}</span>}
      </figcaption>
    </figure>
  );
}
