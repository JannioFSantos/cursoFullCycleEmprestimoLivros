/**
 * Relógio = a única fonte de "agora" da aplicação.
 *
 * Por que não chamar `new Date()` espalhado pelo código? Porque em teste
 * precisamos simular "hoje", por exemplo para provar que um empréstimo
 * venceu. Com esta interface, o teste injeta um relógio controlado e o
 * código de produção usa o relógio real.
 */
export interface Relogio {
  agora(): Date
}

export const relogioDoSistema: Relogio = {
  agora: () => new Date(),
}
